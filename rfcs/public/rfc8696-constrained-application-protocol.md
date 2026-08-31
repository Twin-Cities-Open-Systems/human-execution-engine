# rfcs/public/rfc8696-constrained-application-protocol.md

Internet Engineering Task Force (IETF)                        R. Housley
Request for Comments: 8696                                Vigil Security
Category: Standards Track                                  December 2019
ISSN: 2070-1721

  Using Pre-Shared Key (PSK) in the Cryptographic Message Syntax (CMS)

Abstract

   The invention of a large-scale quantum computer would pose a serious
   challenge for the cryptographic algorithms that are widely deployed
   today.  The Cryptographic Message Syntax (CMS) supports key transport
   and key agreement algorithms that could be broken by the invention of
   such a quantum computer.  By storing communications that are
   protected with the CMS today, someone could decrypt them in the
   future when a large-scale quantum computer becomes available.  Once
   quantum-secure key management algorithms are available, the CMS will
   be extended to support the new algorithms if the existing syntax does
   not accommodate them.  This document describes a mechanism to protect
   today's communication from the future invention of a large-scale
   quantum computer by mixing the output of key transport and key
   agreement algorithms with a pre-shared key.

Status of This Memo

   This is an Internet Standards Track document.

   This document is a product of the Internet Engineering Task Force
   (IETF).  It represents the consensus of the IETF community.  It has
   received public review and has been approved for publication by the
   Internet Engineering Steering Group (IESG).  Further information on
   Internet Standards is available in Section 2 of RFC 7841.

   Information about the current status of this document, any errata,
   and how to provide feedback on it may be obtained at
   <https://www.rfc-editor.org/info/rfc8696>.

Copyright Notice

   Copyright (c) 2019 IETF Trust and the persons identified as the
   document authors.  All rights reserved.

   This document is subject to BCP 78 and the IETF Trust's Legal
   Provisions Relating to IETF Documents
   (<https://trustee.ietf.org/license-info>) in effect on the date of
