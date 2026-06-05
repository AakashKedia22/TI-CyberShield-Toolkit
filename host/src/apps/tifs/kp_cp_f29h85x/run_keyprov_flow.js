// Since we don't know where CCS will be installed, we must find files relative
// to this script. To this end, we will need access to node.js's path functions.
const path = require("path");
const os = require("os");
const fs = require('fs');

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
Usage: node run_keyprov_flow.js [options]
Options:
  --otp-kw-bin <path>     Path to OTP KW binary file (required)
  --certificate <path>     Path to certificate file (required)
  --jtag-kernel <path>     Path to JTAG flash kernel file (required)
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
            case '--otp-kw-bin':
                options.otpKwBin = value;
                break;
            case '--certificate':
                options.certificate = value;
                break;
            case '--jtag-kernel':
                options.jtagKernel = value;
                break;
            default:
                console.error(`Unknown argument: ${arg}`);
                console.log(usage);
                process.exit(1);
        }
    }

    // Validate required arguments
    const requiredArgs = [
        { name: 'otpKwBin', arg: '--otp-kw-bin' },
        { name: 'certificate', arg: '--certificate' },
        { name: 'jtagKernel', arg: '--jtag-kernel' }
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

    return options;
}

// Get file paths from command line arguments
const { otpKwBin, certificate, jtagKernel } = parseArgs();


// Initialize scripting and obtain the main debugger scripting interface
const ds = initScripting({suppressMessages: true});

// Configure a 1 minute timeout on all operations (by default there is no timeout).
// Key provisioning can take >30s (cert processing alone ~3.6s on HS-FS) so 10s is too short.
ds.setScriptingTimeout(60000);

// Configure the debugger and open a debug session to the cortex M core
// Check for PyInstaller temp directory first, then fall back to __dirname
const ccxmlPath = process.env.CCXML_PATH || join(__dirname, "F29h85x-hsse.ccxml");
ds.configure(ccxmlPath);
const session = ds.openSession("Texas Instruments XDS110 USB Debug Probe/C29xx_CPU1");

session.target.connect();

// overwrite file if it already exists
session.cio.beginCapture(join(__dirname, "log.txt"));

session.target.halt();

// Load the OTP KW binary at a fixed address i.e. 0x200E0000
console.log(`Loading OTP KW binary from: ${otpKwBin}`);
session.memory.loadBinary(0x200E0000n, otpKwBin);

// Load the OTP KW certificate at a fixed address i.e. 0x200F8000
console.log(`Loading certificate from: ${certificate}`);
session.memory.loadBinary(0x200F8000n, certificate);

// Write CMD_CTRL_REG bitmask: CMD_BIT_HSM_RT | CMD_BIT_HSM_KEYS
const CMD_BITS_KP = 0x00000003; // CMD_BIT_HSM_RT | CMD_BIT_HSM_KEYS
const cmdBitsBuf = Buffer.allocUnsafe(4);
cmdBitsBuf.writeUInt32LE(CMD_BITS_KP, 0);
const cmdBitsTmpPath = path.join(os.tmpdir(), 'kp_cmd_bits.bin');
fs.writeFileSync(cmdBitsTmpPath, cmdBitsBuf);
console.log(`Writing CMD_CTRL_REG bitmask 0x${CMD_BITS_KP.toString(16).padStart(8,'0').toUpperCase()} to 0x30180508`);
session.memory.loadBinary(0x30180508n, cmdBitsTmpPath);
try { fs.unlinkSync(cmdBitsTmpPath); } catch(e) {}

// Load a JTAG flash Kernel out file to a fixed location
console.log(`Loading JTAG flash kernel from: ${jtagKernel}`);
session.memory.loadProgram(jtagKernel);

//Run the target, till stopped.

try {
	console.log("Expecting target to not halt for 120 seconds");
	session.target.run();
	console.error("Failure: Halted unexpectedly after removing both breakpoints.");
} catch (err) {
	// Check if we actually timed out, or if some other error occurred
	if (err instanceof ScriptingTimeoutError) {
		console.log("Success: we timed out while waiting for the target to halt");
		session.target.halt();
		
	} else {
		console.error(`Failure: unexpected error while running ${err}`);
	}
}

// End CIO capture to flush all buffered output to log.txt before reading it
try { session.cio.endCapture(); } catch(e) {}

// Read and print the contents of log.txt
const logContent = fs.readFileSync(join(__dirname, "log.txt"), 'utf8');
console.log("Log file contents:");
console.log(logContent);

session.target.disconnect();

// shutdown the debugger
ds.shutdown();
