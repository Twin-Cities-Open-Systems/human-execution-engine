# rfcs/public/rfc6749-oauth-2-0.md

Internet Engineering Task Force (IETF)                     D. Hardt, Ed.
Request for Comments: 6749                                     Microsoft
Obsoletes: 5849                                             October 2012
Category: Standards Track
ISSN: 2070-1721

                 The OAuth 2.0 Authorization Framework

Abstract

   The OAuth 2.0 authorization framework enables a third-party
   application to obtain limited access to an HTTP service, either on
   behalf of a resource owner by orchestrating an approval interaction
   between the resource owner and the HTTP service, or by allowing the
   third-party application to obtain access on its own behalf.  This
   specification replaces and obsoletes the OAuth 1.0 protocol described
   in RFC 5849.

Status of This Memo

   This is an Internet Standards Track document.

   This document is a product of the Internet Engineering Task Force
   (IETF).  It represents the consensus of the IETF community.  It has
   received public review and has been approved for publication by the
   Internet Engineering Steering Group (IESG).  Further information on
   Internet Standards is available in Section 2 of RFC 5741.

   Information about the current status of this document, any errata,
   and how to provide feedback on it may be obtained at
   <http://www.rfc-editor.org/info/rfc6749>.

Copyright Notice

   Copyright (c) 2012 IETF Trust and the persons identified as the
   document authors.  All rights reserved.

   This document is subject to BCP 78 and the IETF Trust's Legal
   Provisions Relating to IETF Documents
   (<http://trustee.ietf.org/license-info>) in effect on the date of
   publication of this document.  Please review these documents
   carefully, as they describe your rights and restrictions with respect
   to this document.  Code Components extracted from this document must
   include Simplified BSD License text as described in Section 4.e of
   the Trust Legal Provisions and are provided without warranty as
   described in the Simplified BSD License.

Hardt                        Standards Track                    [Page 1]

RFC 6749                        OAuth 2.0                   October 2012

Table of Contents

   1. Introduction ....................................................4
      1.1. Roles ......................................................6
      1.2. Protocol Flow ..............................................7
      1.3. Authorization Grant ........................................8
           1.3.1. Authorization Code ..................................8
           1.3.2. Implicit ............................................8
           1.3.3. Resource Owner Password Credentials .................9
           1.3.4. Client Credentials ..................................9
      1.4. Access Token ..............................................10
      1.5. Refresh Token .............................................10
      1.6. TLS Version ...............................................12
      1.7. HTTP Redirections .........................................12
      1.8. Interoperability ..........................................12
      1.9. Notational Conventions ....................................13
   2. Client Registration ............................................13
      2.1. Client Types ..............................................14
      2.2. Client Identifier .........................................15
      2.3. Client Authentication .....................................16
           2.3.1. Client Password ....................................16
           2.3.2. Other Authentication Methods .......................17
      2.4. Unregistered Clients ......................................17
   3. Protocol Endpoints .............................................18
      3.1. Authorization Endpoint ....................................18
           3.1.1. Response Type ......................................19
           3.1.2. Redirection Endpoint ...............................19
      3.2. Token Endpoint ............................................21
           3.2.1. Client Authentication ..............................22
      3.3. Access Token Scope ........................................23
   4. Obtaining Authorization ........................................23
      4.1. Authorization Code Grant ..................................24
           4.1.1. Authorization Request ..............................25
           4.1.2. Authorization Response .............................26
           4.1.3. Access Token Request ...............................29
           4.1.4. Access Token Response ..............................30
      4.2. Implicit Grant ............................................31
           4.2.1. Authorization Request ..............................33
