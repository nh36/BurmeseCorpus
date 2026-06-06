# TN 36-57 segmentation note (Plate XXXI / obi-v01-n0052)

## Scope and question

Target: `TN 36-57` / `Plate XXXI` / `List 273` / `PPA 109-111` / `obi-v01-n0052-ob-p0083`  
Question: can one bounded TN translation segment be isolated and linked safely to `obi-v01-n0052`?

## Candidate subsegments inside TN 36-57

| Subsegment | TN pages | OCR pages | Key entry markers | Match to `obi-v01-n0052` |
| --- | --- | --- | --- | --- |
| A | 36-37 | 49-50 | `No. (10)`, `No. (11)` (late-dated entries, 778/804) | Reject |
| B | 47-48 | 60-61 | `No. (1).—OBVERSE` (Thinkaya, 804) | Reject |
| C | 49-56 | 62-69 | `No. (2)` through `No. (11)` | Reject |
| **D** | **56-57** | **69-70 (before `REVERSE.`)** | **`No. (1).—OBVERSE` / `Locality... Kemawaya pagoda` / `Date 569` / `Founder. King Nandaungmya` | **Accept** |
| E | 57+ | 70+ | `REVERSE.` block (Date 609, different founders) | Exclude from obverse target |

## Match evidence

1. Structured record `obi-v01-n0052-ob-p0083` metadata matches subsegment D exactly on the decisive identifiers: Khemavara/Kemawaya context, date `CS 569`, donor `King Nadaungmya`.
2. TN subsegment D explicitly states: locality within Kemawaya pagoda walls, date 569 Sakkaraj (1207 A.D.), founder King Nandaungmya, and a land-dedication summary.
3. Cross-witness concordance aligns this same record cluster: Plate XXXI + List 273 + PPA 109-111 + TN p.56 + SIP linkage (`sip-unit-006` / `sip-witness-006-seg-01` linked to `obi-v01-n0052-ob-p0083`).
4. Boundary isolation is now explicit and safe: start at `No. (1).—OBVERSE` + Kemawaya line; end at `REVERSE.`.

## Decision

Integrate subsegment D as a bounded TN partial translation for `obi-v01-n0052-ob-p0083` using the exact subentry boundary above.

## What remains missing

No additional evidence is needed for the obverse match itself. The reverse block is intentionally excluded because the target record is the obverse record (`...-ob-p0083`), not the reverse continuation.
