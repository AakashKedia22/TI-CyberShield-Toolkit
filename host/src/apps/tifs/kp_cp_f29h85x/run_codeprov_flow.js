// Since we don't know where CCS will be installed, we must find files relative
// to this script. To this end, we will need access to node.js's path functions.
const path = require("path");
const os = require("os");
const fs = require("fs");

// Platform-specific handling
const isWindows = os.platform() === 'win32';
const join = path.join;

// Parse command line arguments
function parseArgs() {
    // When run directly with node, process.argv[0] is 'node', process.argv[1] is the script path
    // When run through run.sh, process.argv[0] is the node path, process.argv[1] is launcher.mjs, 
    // process.argv[2] is the script path, and the actual arguments start at process.argv[3]
    const isRunThroughLauncher = process.argv[1].endsWith('launcher.mjs');
    const args = isRunThroughLauncher ? process.argv.slice(3) : process.argv.slice(2);
    const usage = `
Usage: node run_codeprov_flow.js [options]
Options:
  --hsm-image <path>       Path to HSM image file (required)
  --jtag-kernel <path>     Path to JTAG flash kernel file (required)
  --hsm-cpu-code <path>    Path to HSM CPU code file (optional)
  --c29-cpu-code <path>    Path to C29 CPU1 code file (optional)
  --c29-cpu3-code <path>   Path to C29 CPU3 code file (optional; same load address as CPU1)
  --seccfg       <path>    Path to C29 CPU SECCFG file (optional)
  --help                   Show this help message
`;

    if (args.includes('--help') || args.length === 0) {
        console.log(usage);
        process.exit(args.includes('--help') ? 0 : 1);
    }

    const options = {};
    for (let i = 0; i < args.length; i += 2) {
        if (i + 1 >= args.length) {
            console.error(`Missing value for argument ${args[i]}`);
            console.log(usage);
            process.exit(1);
        }
        
        const arg = args[i];
        const value = args[i + 1];
        
        switch (arg) {
            case '--hsm-image':
                options.hsmImage = value;
                break;
            case '--jtag-kernel':
                options.jtagKernel = value;
                break;
            case '--hsm-cpu-code':
                options.hsmCpuCode = value;
                break;
            case '--c29-cpu-code':
                options.c29CpuCode = value;
                break;
            case '--c29-cpu3-code':
                options.c29Cpu3Code = value;
                break;
            case '--seccfg':
                options.seccfgBin = value;
                break;
            default:
                console.error(`Unknown argument: ${arg}`);
                console.log(usage);
                process.exit(1);
        }
    }

    // Validate required arguments
    const requiredArgs = [
        { name: 'hsmImage', arg: '--hsm-image' },
        { name: 'jtagKernel', arg: '--jtag-kernel' },
    ];

    for (const { name, arg } of requiredArgs) {
        if (!options[name]) {
            console.error(`Missing required argument: ${arg}`);
            console.log(usage);
            process.exit(1);
        }

        // Check if file exists
        if (!fs.existsSync(options[name])) {
            console.error(`File not found: ${options[name]}`);
            process.exit(1);
        }
    }

    // Validate optional arguments if provided
    if (options.hsmCpuCode && !fs.existsSync(options.hsmCpuCode)) {
        console.error(`File not found for --hsm-cpu-code: ${options.hsmCpuCode}`);
        process.exit(1);
    }
    if (options.c29CpuCode && !fs.existsSync(options.c29CpuCode)) {
        console.error(`File not found for --c29-cpu-code: ${options.c29CpuCode}`);
        process.exit(1);
    }
    if (options.c29Cpu3Code && !fs.existsSync(options.c29Cpu3Code)) {
        console.error(`File not found for --c29-cpu3-code: ${options.c29Cpu3Code}`);
        process.exit(1);
    }
    if (options.seccfgBin && !fs.existsSync(options.seccfgBin)) {
        console.error(`File not found for --seccfg: ${options.seccfgBin}`);
        process.exit(1);
    }

    return options;
}

// Get file paths from command line arguments
const { hsmImage, jtagKernel, hsmCpuCode, c29CpuCode, c29Cpu3Code, seccfgBin } = parseArgs();


// Constants for chunk sizes
const FIRST_CHUNK_SIZE = 0x1000; // 4KB
const CHUNK_SIZE = 0x4000; // 16KB

// Function to create temporary directory
function createTempDir() {
    // Create a platform-independent temp directory
    const tempDir = join(os.tmpdir(), 'code_prov_chunks');
    if (!fs.existsSync(tempDir)) {
        fs.mkdirSync(tempDir);
    }
    return tempDir;
}

// Function to clean up temporary directory
function cleanupTempDir(tempDir) {
    if (fs.existsSync(tempDir)) {
        fs.readdirSync(tempDir).forEach(file => {
            fs.unlinkSync(join(tempDir, file));
        });
        fs.rmdirSync(tempDir);
    }
}

// Function to run target with timeout handling
function runTargetWithTimeout(session) {
    try {
        //console.log("Expecting target to not halt for 10 seconds");
        session.target.run();
    } catch (err) {
        if (err instanceof ScriptingTimeoutError) {
            console.log("Success: we timed out while waiting for the target to halt");
            session.target.halt();
        } else {
            throw err;
        }
    }
}

// Function to process file in chunks
function processFileInChunks(filePath, session, tempDir) {
    console.log(`Processing file: ${filePath}`);
    const fileSize = fs.statSync(filePath).size;
    const fileData = fs.readFileSync(filePath);
    
    // Process first chunk (4KB)
    const firstChunkPath = join(tempDir, "chunk_0.bin");
    fs.writeFileSync(firstChunkPath, fileData.slice(0, FIRST_CHUNK_SIZE));
    
    // Load and process first chunk
    session.memory.loadBinary(0x200F8000n, firstChunkPath);
    //console.log(`Loaded first chunk of ${FIRST_CHUNK_SIZE} bytes at address 0x200F8000`);
    runTargetWithTimeout(session);
    
    // Process remaining chunks
    let remainingSize = fileSize - FIRST_CHUNK_SIZE;
    let chunkNumber = 1;
    let offset = FIRST_CHUNK_SIZE;
    
    while (remainingSize > 0) {
        const currentChunkSize = Math.min(CHUNK_SIZE, remainingSize);
        const chunkPath = join(tempDir, `chunk_${chunkNumber}.bin`);
        
        // Create chunk file
        fs.writeFileSync(chunkPath, fileData.slice(offset, offset + currentChunkSize));
        
        // Load and process chunk
        session.memory.loadBinary(0x200F8000n, chunkPath);
        //console.log(`Loaded chunk ${chunkNumber} of size ${currentChunkSize} bytes at address 0x200F8000`);
        runTargetWithTimeout(session);
        
        // Update for next iteration
        remainingSize -= currentChunkSize;
        offset += currentChunkSize;
        chunkNumber++;
    }
}

// Initialize scripting and obtain the main debugger scripting interface
const ds = initScripting({suppressMessages: true});

// Configure a 10 second timeout on all operations (by default there is no timeout)
ds.setScriptingTimeout(10000);

// Configure the debugger and open a debug session to the cortex M core
// Check for PyInstaller temp directory first, then fall back to __dirname
const ccxmlPath = process.env.CCXML_PATH || join(__dirname, "F29h85x-hsse.ccxml");
ds.configure(ccxmlPath);
const session = ds.openSession("Texas Instruments XDS110 USB Debug Probe/C29xx_CPU1");

session.target.connect();

// overwrite file if it already exists
session.cio.beginCapture(join(__dirname, "log.txt"));

session.target.halt();

// Load the HSM image at fixed address 0x200E0000
console.log(`Loading HSM image from: ${hsmImage}`);
session.memory.loadBinary(0x200E0000n, hsmImage);

// Load a JTAG flash Kernel out file to a fixed location
console.log(`Loading JTAG flash kernel from: ${jtagKernel}`);
session.memory.loadProgram(jtagKernel);

// Create temporary directory for chunks
const tempDir = createTempDir();

// CMD_CTRL_REG bit definitions (must match ex3_jtag_get_function_cpu1.h)
const CMD_BIT_HSM_RT  = (1 << 0);
const CMD_BIT_HSM_CP  = (1 << 2);
const CMD_BIT_CPU1_CP = (1 << 3);
const CMD_BIT_CPU3_CP = (1 << 4);
const CMD_BIT_SEC_CFG = (1 << 5);

// Compute bitmask from provided inputs
let cmdBits = CMD_BIT_HSM_RT;
if (hsmCpuCode)  cmdBits |= CMD_BIT_HSM_CP;
if (c29CpuCode)  cmdBits |= CMD_BIT_CPU1_CP;
if (c29Cpu3Code) cmdBits |= CMD_BIT_CPU3_CP;
if (seccfgBin)   cmdBits |= CMD_BIT_SEC_CFG;

// Write cmdBits to CMD_CTRL_REG (0x30180508) so the kernel reads it at startup
console.log(`Writing CMD_CTRL_REG bitmask 0x${cmdBits.toString(16).padStart(8, '0').toUpperCase()} to 0x30180508`);
const cmdBitsBuf = Buffer.allocUnsafe(4);
cmdBitsBuf.writeUInt32LE(cmdBits, 0);
const cmdBitsPath = path.join(tempDir, "cmd_bits.bin");
fs.writeFileSync(cmdBitsPath, cmdBitsBuf);
session.memory.loadBinary(0x30180508n, cmdBitsPath);

try {
    // Phase 1: HSM CPU Code Provisioning
    if (hsmCpuCode) {
        console.log("Moving to HSM CPU Code Provisioning");
        processFileInChunks(hsmCpuCode, session, tempDir);
    }

    // Phase 2: C29 CPU1 Code Provisioning
    if (c29CpuCode) {
        console.log("Moving to C29 CPU1 Code Provisioning");
        processFileInChunks(c29CpuCode, session, tempDir);
    }

    // Phase 2.5: C29 CPU3 Code Provisioning (optional, same load address as CPU1)
    if (c29Cpu3Code) {
        console.log("Moving to C29 CPU3 Code Provisioning");
        processFileInChunks(c29Cpu3Code, session, tempDir);
    }

    // Phase 3: C29 CPU SECCFG Code Provisioning
    if (seccfgBin) {
        session.memory.loadBinary(0x200F8000n, seccfgBin);
        runTargetWithTimeout(session);
    }
    
} catch (err) {
    console.error(`Error during code provisioning: ${err}`);
    throw err;
} finally {
    // Clean up temporary files
    cleanupTempDir(tempDir);
    
    // Read and print the contents of log.txt
    const logContent = fs.readFileSync(join(__dirname, "log.txt"), 'utf8');
    console.log("Log file contents:");
    console.log(logContent);

    session.target.disconnect();    
    // shutdown the debugger
    ds.shutdown();
}
