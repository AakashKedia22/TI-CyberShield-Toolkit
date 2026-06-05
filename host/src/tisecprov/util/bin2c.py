"""
Functions to convert a binary blob to a C header file.
"""

import os
from datetime import datetime


def get_current_year() -> int:  # pylint: disable=missing-function-docstring
    return datetime.today().year


def get_license(license_name: str) -> str:  # pylint: disable=missing-function-docstring
    licenses = {
        "ti_tspa": TSPA_LICENSE,
        "ti_lic": TI_LICENSE,
    }
    if licenses.get(license_name) is None:
        raise ValueError(f"Unknown license: {license_name}")
    return licenses[license_name]


TI_LICENSE = """
/*
 *  Copyright (C) {year} Texas Instruments Incorporated
 *
 *  Redistribution and use in source and binary forms, with or without
 *  modification, are permitted provided that the following conditions
 *  are met:
 *
 *    Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 *
 *    Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the
 *    distribution.
 *
 *    Neither the name of Texas Instruments Incorporated nor the names of
 *    its contributors may be used to endorse or promote products derived
 *    from this software without specific prior written permission.
 *
 *  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 *  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 *  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 *  A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 *  OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 *  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 *  LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 *  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 *  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 *  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 *  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */
"""

TSPA_LICENSE = """
/*
* TI TSPA License
* TECHNOLOGY AND SOFTWARE PUBLICLY AVAILABLE
* SOFTWARE LICENSE
*
* Copyright (c) {year}, Texas Instruments Incorporated.
*
* All rights reserved not granted herein.
*
* Limited License.
*
* Texas Instruments Incorporated grants a world-wide, royalty-free, non-exclusive
* license under copyrights and patents it now or hereafter owns or controls to
* make, have made, use, import, offer to sell and sell ("Utilize") this software,
* but solely to the extent that any such patent is necessary to Utilize the
* software alone. The patent license shall not apply to any combinations which
* include this software.  No hardware per se is licensed hereunder.
*
* Redistribution and use in binary form, without modification, are permitted
* provided that the following conditions are met:
*
* * Redistributions must preserve existing copyright notices and reproduce this
* license (including the above copyright notice and the disclaimer below) in the
* documentation and/or other materials provided with the distribution.
*
* * Neither the name of Texas Instruments Incorporated nor the names of its
* suppliers may be used to endorse or promote products derived from this software
* without specific prior written permission.
*
* * No reverse engineering, decompilation, or disassembly of this software is
* permitted.
*
* * Nothing shall obligate TI to provide you with source code for the software
* licensed and provided to you in object code.
*
* DISCLAIMER.
*
* THIS SOFTWARE IS PROVIDED BY TI AND TIS LICENSORS "AS IS" AND ANY EXPRESS OR
* IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
* MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
* EVENT SHALL TI AND TIS LICENSORS BE LIABLE FOR ANY DIRECT, INDIRECT,
* INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
* LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
* PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
* LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
* NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
* EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*
*/
"""

HEADER = """{license}

#ifndef {header_name}_H_
#define {header_name}_H_

#ifdef __cplusplus
extern "C"
{{
#endif

#define {array_name}_SIZE_IN_BYTES ({size}U)

#define {array_name} {{ \\
"""

FOOTER = """
}} /* {infilesize} bytes */

#ifdef __cplusplus
}}
#endif

#endif /* {header_name}_H_ */
"""


def generate_c_header(
    infile, outfile_path: str, array_name: str, header_name: str, license_type: str
):
    """
    Generate a C header file with the given header_name and license text
    corresponding to the license_type, which defines an array of uint8_t
    with the given array_name, which contains an array of bytes representing
    the contents of infile.
    """
    # get the license text with copyright year
    license_text = get_license(license_type).format(year=get_current_year())
    with open(outfile_path, mode="w", encoding="utf-8") as outfile:
        infile.seek(0, os.SEEK_END)
        infilesize = infile.tell()
        infile.seek(0)

        # write header
        outfile.write(
            HEADER.format(
                license=license_text,
                header_name=header_name.upper(),
                array_name=array_name.upper(),
                size=infilesize,
            )
        )
        outfile.write("    ")

        count = 0
        while True:
            # read a byte at a time
            byte = infile.read(1)
            if not byte:
                break

            count = count + 1
            # make it into an ascii C hex formatted byte
            outfile.write(f"0x{byte.hex()}U, ")
            # break to new line after 16 bytes
            if count == 16:
                outfile.write(" \\\n    ")
                count = 0

        outfile.write(" \\")
        outfile.write(
            FOOTER.format(infilesize=infilesize, header_name=header_name.upper())
        )
