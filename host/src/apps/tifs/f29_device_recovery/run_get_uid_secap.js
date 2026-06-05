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
  if (nonDebugCores.length < 3) {
    console.error('Not enough cores available');
    ds.shutdown();
    return;
  }
  const secapHSM = ds.openSession(nonDebugCores[2]);
  if (secapHSM && secapHSM.target) {
    try {
      secapHSM.target.connect();
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
  // Writing Get UID Command to HSM Secap
  try {
    secapHSM.registers.write("TRANSMIT_CONTROL", "0x00010000");
    // console.log("Wrote to TRANSMIT_CONTROL");
    secapHSM.registers.write("TRANSMIT_DATA", "0x80B5729F");
    // console.log("Wrote to TRANSMIT_DATA");
  } catch (error) {
    console.error(`Error writing to registers: ${error}`);
    ds.shutdown();
    return;
  }

console.log("--->> SOC info request sent. Waiting for response. \n");
let receivedData = [];
for (let i = 0; i < 16; i++) {
    let rcr;
    try {
      rcr = Number(secapHSM.registers.read("RECEIVE_CONTROL"));
      // console.log(`Read from RECEIVE_CONTROL: ${rcr.toString(16)}`);
    } catch (error) {
      console.error(`Error reading from register: ${error}`);
      ds.shutdown();
      return;
    }
    while ((rcr & 0x00000001) === 0) {
      try {
        rcr = Number(secapHSM.registers.read("RECEIVE_CONTROL"));
        // console.log(`Read from RECEIVE_CONTROL: ${rcr.toString(16)}`);
      } catch (error) {
        console.error(`Error reading from register: ${error}`);
        ds.shutdown();
        return;
      }
    }
    let rdr;
    try {
      rdr = Number(secapHSM.registers.read("RECEIVE_DATA"));
      // console.log(`Read from RECEIVE_DATA: ${rdr.toString(16)}`);
      let hexString = rdr.toString(16).padStart(8, '0').toUpperCase(); // Convert to uppercase and pad with zeros
      let reversedHexString = hexString.match(/.{2}/g).reverse().join(''); // Reverse the byte order
      receivedData.push(reversedHexString); // Store the value in the array
    } catch (error) {
      console.error(`Error reading from register: ${error}`);
      ds.shutdown();
      return;
    }
}

// Create a string from the received data
let receivedString = receivedData.join('');
console.log(`Received UID: ${receivedString}`);
  console.log("\n--->> SOCinfo test done\n");
} catch (error) {
  console.error(`Error configuring debugger: ${error}`);
} finally {
  ds.shutdown();
}