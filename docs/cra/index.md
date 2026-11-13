# Cyber Resilience Act (CRA)

The EU Cyber Resilience Act (Regulation (EU) 2024/2847) sets cybersecurity rules for software
and hardware that is made available on the EU market. This section collects what it may mean for
Tapir: whether it applies, what it would require, and where Tapir stands today.

!!! warning "Not legal advice"
    These pages are a technical assessment to start a discussion, not a legal opinion. Whether
    and how the CRA applies to Tapir and FoodCoopX has to be confirmed by someone with legal
    expertise. Open points are marked as **open**.

## Pages

| Page | Content |
|---|---|
| [Scope](scope.md) | Does the CRA apply to Tapir, and who would be the manufacturer? |
| [Requirements](requirements.md) | What the CRA asks for, and where Tapir stands today |
| [Relation to the GDPR](gdpr.md) | Where the CRA and the GDPR overlap, especially deletion (#1123) |

## Timeline

| Date | What applies |
|---|---|
| 11 September 2026 | Reporting obligations: actively exploited vulnerabilities and severe incidents have to be reported (Art. 14) |
| 11 December 2027 | Full application: essential requirements, vulnerability handling, technical documentation, conformity assessment |

The reporting obligations already apply. That makes a way to receive and handle vulnerability
reports the most urgent point, see [Requirements](requirements.md#vulnerability-handling).

## Suggested first steps

1. Clarify the scope question with legal advice ([Scope](scope.md)).
2. Add a `SECURITY.md` with a contact for vulnerability reports. This is useful whether or not
   the CRA applies.
3. Decide who at FoodCoopX is responsible for security reports and for reporting to the
   authorities.
4. Go through the [Requirements](requirements.md) and turn the open points into issues.
