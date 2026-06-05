// Since we don't know where CCS will be installed, we must find files relative
// to this script. To this end, we will need access to node.js's path.join function.
const { join } = require("path");
const fs = require("fs");
const os = require("os");

// Initialize scripting and obtain the main debugger scripting interface
const ds = initScripting({suppressMessages: true});
// Configure a 10 second timeout on all operations (by default there is no timeout)
ds.setScriptingTimeout(10000);
try {
  // Configure the debugger and open a debug session to the cortex M core
  const { cores, nonDebugCores } = ds.configure(join(__dirname, "F29h85x-hsse.ccxml"));
  console.log(`Non-debug cores: ${nonDebugCores}`);
  if (nonDebugCores.length < 2) {
    console.error('Not enough cores available');
    ds.shutdown();
    return;
  }
  const secapC29 = ds.openSession(nonDebugCores[1]);
  if (secapC29 && secapC29.target) {
    try {
      secapC29.target.connect();
    } catch (error) {
      console.error(`Error connecting to target: ${error}`);
      ds.shutdown();
      return;
    }
  } else {
    console.error('Failed to open session to HSM');
    ds.shutdown();
    return;
  }
  // Writing Device Recovery Command to C29 Secap
  try {
    secapC29.registers.write("TRANSMIT_CONTROL", "0x244");
    secapC29.registers.write("TRANSMIT_DATA", "0x65EA6103");
  } catch (error) {
    console.error(`Error writing to registers: ${error}`);
    ds.shutdown();
    return;
  }
  try {
    secapC29.target.halt();
  } catch (error) {
    console.error(`Error halting target: ${error}`);
  }
} catch (error) {
  console.error(`Error configuring debugger: ${error}`);
} finally {
  ds.shutdown();
}