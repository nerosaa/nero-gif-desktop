# Ed25519 implementation notice

`nero_gif/_ed25519.py` is a small pure-Python Ed25519 (sign + verify) adapted
from the Python reference implementation in **RFC 8032, Section 6**
("Edwards-Curve Digital Signature Algorithm (EdDSA)", S. Josefsson,
I. Liusvaara, January 2017).

Copyright (c) 2017 IETF Trust and the persons identified as the document
authors. All rights reserved.

Code Components extracted from IETF documents are licensed under the
Simplified BSD License (BSD-2-Clause), per Section 4.e of the IETF Trust's
Legal Provisions Relating to IETF Documents (https://trustee.ietf.org/license-info):

> Redistribution and use in source and binary forms, with or without
> modification, are permitted provided that the following conditions are met:
>
> 1. Redistributions of source code must retain the above copyright notice,
>    this list of conditions and the following disclaimer.
> 2. Redistributions in binary form must reproduce the above copyright
>    notice, this list of conditions and the following disclaimer in the
>    documentation and/or other materials provided with the distribution.
>
> THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
> AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
> IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
> ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
> LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
> CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
> SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
> INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
> CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
> ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
> POSSIBILITY OF SUCH DAMAGE.

Local changes: module packaging, strict verification (rejects S >= L and
invalid point encodings), cross-checked against `cryptography` and the
RFC 8032 test vector 1 (`tests/test_license.py`). Not constant-time; the
shipped app only *verifies* with a public key. Signing runs offline.
