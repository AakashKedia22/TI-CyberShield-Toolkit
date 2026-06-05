# Copyright (C) 2026 Texas Instruments Incorporated
#
# All rights reserved not granted herein.
# Limited License.
#
# Texas Instruments Incorporated grants a world-wide, royalty-free,
# non-exclusive license under copyrights and patents it now or hereafter
# owns or controls to make, have made, use, import, offer to sell and sell ("Utilize")
# this software subject to the terms herein.  With respect to the foregoing patent
# license, such license is granted  solely to the extent that any such patent is necessary
# to Utilize the software alone.  The patent license shall not apply to any combinations which
# include this software, other than combinations with devices manufactured by or for TI ("TI Devices").
# No hardware patent is licensed hereunder.
#
# Redistributions must preserve existing copyright notices and reproduce this license (including the
# above copyright notice and the disclaimer and (if applicable) source code license limitations below)
# in the documentation and/or other materials provided with the distribution
#
# Redistribution and use in binary form, without modification, are permitted provided that the following
# conditions are met:
#
#    * No reverse engineering, decompilation, or disassembly of this software is permitted with respect to any
#     software provided in binary form.
#    * any redistribution and use are licensed by TI for use only with TI Devices.
#    * Nothing shall obligate TI to provide you with source code for the software licensed and provided to you in object code.
#
# If software source code is provided to you, modification and redistribution of the source code are permitted
# provided that the following conditions are met:
#
#   * any redistribution and use of the source code, including any resulting derivative works, are licensed by
#     TI for use only with TI Devices.
#   * any redistribution and use of any object code compiled from the source code and any resulting derivative
#     works, are licensed by TI for use only with TI Devices.
#
# Neither the name of Texas Instruments Incorporated nor the names of its suppliers may be used to endorse or
# promote products derived from this software without specific prior written permission.
#
# DISCLAIMER.
#
# THIS SOFTWARE IS PROVIDED BY TI AND TI'S LICENSORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING,
# BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL TI AND TI'S LICENSORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import pytest
import os
from tisecprov.util.bin2c import generate_c_header, get_license, get_current_year

# src/tisecprov/util/test_bin2c.py


@pytest.fixture
def tmp_input_file(tmp_path):
    input_file = tmp_path / "input.bin"
    with open(input_file, "wb") as f:
        f.write(b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10")
    return input_file


@pytest.fixture
def tmp_output_file(tmp_path):
    return tmp_path / "output.h"


def test_generate_c_header(tmp_input_file, tmp_output_file):
    with open(tmp_input_file, "rb") as infile:
        generate_c_header(
            infile, str(tmp_output_file), "test_array", "test_header", "ti_lic"
        )
    with open(tmp_output_file, "r") as f:
        content = f.read()
    assert "#ifndef TEST_HEADER_H_" in content
    assert "#define TEST_HEADER_H_" in content
    assert (
        "0x01U, 0x02U, 0x03U, 0x04U, 0x05U, 0x06U, 0x07U, 0x08U, 0x09U, 0x0aU, 0x0bU, 0x0cU, 0x0dU, 0x0eU, 0x0fU, 0x10U"
        in content
    )


def test_generate_c_header_invalid_license(tmp_input_file, tmp_output_file):
    with open(tmp_input_file, "rb") as infile:
        with pytest.raises(ValueError, match="Unknown license: invalid_license"):
            generate_c_header(
                infile,
                str(tmp_output_file),
                "test_array",
                "test_header",
                "invalid_license",
            )


def test_generate_c_header_empty_input(tmp_path, tmp_output_file):
    empty_input_file = tmp_path / "empty_input.bin"
    empty_input_file.touch()
    with open(empty_input_file, "rb") as infile:
        generate_c_header(
            infile, str(tmp_output_file), "test_array", "test_header", "ti_lic"
        )
    with open(tmp_output_file, "r") as f:
        content = f.read()
    assert "#ifndef TEST_HEADER_H_" in content
    assert "#define TEST_HEADER_H_" in content
    assert "0x" not in content
