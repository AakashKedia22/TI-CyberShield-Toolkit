// Since we don't know where CCS will be installed, we must find files relative
// to this script. To this end, we will need access to node.js's path.join function.
const { join } = require("path");
const fs = require("fs");
const os = require("os");

// Parse command line arguments
function parseArgs() {
    // When run directly with node, process.argv[0] is 'node', process.argv[1] is the script path
    // When run through run.sh, process.argv[0] is the node path, process.argv[1] is launcher.mjs, 
    // process.argv[2] is the script path, and the actual arguments start at process.argv[3]
    const isRunThroughLauncher = process.argv[1].endsWith('launcher.mjs');
    const args = isRunThroughLauncher ? process.argv.slice(3) : process.argv.slice(2);
    const usage = `
Usage: node run_device_recovery_flow.js [options]
Options:
  --dev_recov_cert <path> Path to the device recovery certificate
  --help                  Show this help message
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
            case '--dev_recov_cert':
                options.dev_recov_cert = value;
                break;
            default:
                console.error(`Unknown argument: ${arg}`);
                console.log(usage);
                process.exit(1);
        }
    }

    // Validate required arguments
    const requiredArgs = [
        { name: 'dev_recov_cert', arg: '--dev_recov_cert' }
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
const { dev_recov_cert } = parseArgs();

// Constants for chunk sizes
const CHUNK_SIZE = 0x4; // 4B

// Initialize scripting and obtain the main debugger scripting interface
const ds = initScripting({suppressMessages: true});
// Configure a 10 second timeout on all operations (by default there is no timeout)
ds.setScriptingTimeout(10000);
// Configure the debugger and open a debug session to the cortex M core
let nonDebugCores;
try {
  const { cores, nonDebugCores: ndc } = ds.configure(join(__dirname, "F29h85x-hsse.ccxml"));
  nonDebugCores = ndc;
  if (nonDebugCores) {
    console.log(`Non-debug cores: ${nonDebugCores.length}`);
  } else {
    console.error('No non-debug cores available');
    nonDebugCores = [];
  }
} catch (error) {
  console.error(`Error configuring debugger: ${error}`);
  nonDebugCores = [];
}

let secapHSM = null;
if (nonDebugCores && nonDebugCores.length > 2) {
  try {
    secapHSM = ds.openSession(nonDebugCores[2]);
    if (secapHSM && secapHSM.target) {
      try {
        secapHSM.target.connect();
      } catch (error) {
        console.error(`Error connecting to target: ${error}`);
      }
    } else {
      console.error('Failed to open session to HSM');
    }
  } catch (error) {
    console.error(`Error opening session to HSM: ${error}`);
  }
} else {
  console.error('Not enough cores available');
}
if (secapHSM) {
  try {
    // Writing Validate Device Recovery Cert to HSM Secap
    secapHSM.registers.write("TRANSMIT_CONTROL", "0x00010000");
    secapHSM.registers.write("TRANSMIT_DATA", "0x35131696");
    let tcr = Number(secapHSM.registers.read("TRANSMIT_CONTROL"));
    console.log("--->> Waiting for the override command to be consumed by target \n");
    while (tcr === 0x00010001) {
      console.log("--->> Waiting for the override command to be consumed by target \n");
      tcr = Number(secapHSM.registers.read("TRANSMIT_CONTROL"));
    }
      console.log("--->> Override request sent. \n");
  } catch (error) {
    console.error(`Error writing to or reading from registers: ${error}`);
  }
} else {
  console.error('Failed to open session to HSM');
}

// Function to process device recovery certificate via TRANSMIT_DATA flow
function processDeviceRecoveryCert(filePath, secapHSM) {
    console.log(`Processing device recovery certificate: ${filePath}`);
    
    let fileSize;
    try {
        fileSize = fs.statSync(filePath).size;
        console.log(`File size: ${fileSize} bytes`);
    } catch (err) {
        console.error(`Error getting file size: ${err}`);
        throw err;
    }
    
    // Read the entire file
    const fileData = fs.readFileSync(filePath);
    console.log(`Successfully read ${fileData.length} bytes from file`);
    
    // Calculate total number of chunks
    const totalChunks = Math.ceil(fileSize / CHUNK_SIZE);
    console.log(`Total chunks to process: ${totalChunks}`);
    
    // Process file in 4-byte chunks via TRANSMIT_DATA in reverse order
    let offset = 0;
    let sequentialChunkIndex = 1;
    
    while (offset < fileSize) {
        const currentChunkSize = Math.min(CHUNK_SIZE, fileSize - offset);
        const chunkData = fileData.slice(offset, offset + currentChunkSize);
        
        // Convert chunk to 32-bit value (little-endian) with proper unsigned handling
        let dataValue = 0;
        for (let i = 0; i < currentChunkSize; i++) {
            dataValue |= (chunkData[i] << (i * 8));
        }
        
        // Ensure unsigned 32-bit value
        dataValue = dataValue >>> 0;
        
        // Calculate reverse chunk number (totalChunks, totalChunks-1, ..., 1)
        const chunkNumber = totalChunks - sequentialChunkIndex + 1;
        
        console.log(`Processing chunk ${chunkNumber} (sequential index ${sequentialChunkIndex}): offset=${offset}, size=${currentChunkSize}, data=0x${dataValue.toString(16).padStart(8, '0')}`);
        
        try {
            // Set TRANSMIT_CONTROL with chunk number in upper 16 bits
            const transmitControlValue = (chunkNumber << 16);
            secapHSM.registers.write("TRANSMIT_CONTROL", `0x${transmitControlValue.toString(16).padStart(8, '0')}`);            
            // Write data to TRANSMIT_DATA register
            secapHSM.registers.write("TRANSMIT_DATA", `0x${dataValue.toString(16).padStart(8, '0')}`);

            // Wait for the target to set the ready bit: (chunkNumber << 16) | 0x0001
            const expectedValue = (chunkNumber << 16) | 0x00000001;
            console.log(`Waiting for chunk ${chunkNumber} to be consumed by target (expecting 0x${expectedValue.toString(16).padStart(8, '0')})...`);
            let tcr = Number(secapHSM.registers.read("TRANSMIT_CONTROL"));
            while (tcr === expectedValue) {
                tcr = Number(secapHSM.registers.read("TRANSMIT_CONTROL"));
              }
            
        } catch (error) {
            console.error(`Error transmitting chunk ${chunkNumber}: ${error}`);
            throw error;
        }
        
        // Update for next iteration
        offset += currentChunkSize;
        sequentialChunkIndex++;
    }
    
    console.log(`Successfully transmitted ${totalChunks} chunks (${fileSize} bytes total) in reverse order`);
    let tcr = secapHSM.registers.read("RECEIVE_CONTROL");
    while ((tcr & 0x0001n) === 0n) {
        tcr = secapHSM.registers.read("RECEIVE_CONTROL");
        console.log("Waiting for Response");
    }

    let rdr = secapHSM.registers.read("RECEIVE_DATA");
    if (rdr === 0xDEAD3A17n) {
        console.log("--->> OVERRIDE DONE: WIR_RESPONSE_SUCCESS");
    } else if (rdr === 0xDEADFA17n) {
        console.log("--->> OVERRIDE FAIL: WIR_RESPONSE_FAILURE");
    } else {
        console.log(`--->> ERROR! Invalid response: 0x${rdr.toString(16).padStart(8, '0')}`);
    }
    console.log("\n--->> Override test done\n");
}

try {
    if (secapHSM) {
        console.log("Starting Device Recovery Certificate transmission via TRANSMIT_DATA flow");
        
        // Process the device recovery certificate
        processDeviceRecoveryCert(dev_recov_cert, secapHSM);
        
        console.log("Device Recovery Certificate transmission completed successfully");
    } else {
        console.error("Cannot proceed: HSM session not available");
        process.exit(1);
    }
    
} catch (err) {
    console.error(`Error during device recovery certificate processing: ${err}`);
    throw err;
} finally {
    // shutdown the debugger
    ds.shutdown();
}
