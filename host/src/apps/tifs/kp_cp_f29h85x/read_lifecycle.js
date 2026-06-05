// Since we don't know where CCS will be installed, we must find files relative
// to this script. To this end, we will need access to node.js's path functions.
const path = require("path");
const os = require("os");
const fs = require("fs");

// Platform-specific handling
const isWindows = os.platform() === 'win32';
const join = path.join;


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

// Read 32 bytes of DevCfg.DevLifeCycle
let values = session.memory.read(0x301803D4n, 1, 32);

// Extract HSSUBTYPE field (bits 11-8)
const hssubtype = (values >> 8) & 0xF;

// Check device state based on HSSUBTYPE field values
if (hssubtype === 0x3) { // KP - Keys Provisioned
    console.log("Device is in HS_KP state");
} else if (hssubtype === 0xA) { // FS - Field Securable
    console.log("Device is in HS_FS state");
} else if (hssubtype === 0xF) { // Not FA, so must be SE
    console.log("Device is in HS_FA state");
} else {
    console.log("Device is in HS_SE state");
}

// shutdown the debugger
ds.shutdown();
