# Solved-sample evidence inventory

Input-side inventory only. Expected output columns were not inspected to derive facts.

| Request | Evidence | Required fact | Normalized target |
| --- | --- | --- | --- |
| request_02 | message_01 | ongoing salary amount/effective date | salary stream amendment |
| request_03 | message_02 + image_01 | payroll continuation; net pay | salary stream + event_253 amount |
| request_04 | message_03 | unapproved bonus remains unavailable | informational/no cash change |
| request_06 | message_04 | next-payroll salary amount | one salary occurrence |
| request_07 | message_05 | changed confirmed pay date | scheduled salary event date |
| request_08 | message_06 | next-payroll salary amount | one salary occurrence |
| request_10 | message_07 | payout pending/not withdrawable | informational/no cash change |
| request_11 | message_08 | confirmed base salary; commission unavailable | salary stream + no cash change |
| request_12 | message_09 | seasonal income termination | salary stream termination |
| request_14 | message_10 | salary resumes; childcare begins | stream amendments (amount/date/classification) |
| request_15 | message_11 | first salary amount/date | scheduled salary occurrence |
| request_16 | message_12 + image_02 | rent increase; balance due | rent stream percentage + event_1442 amount |
| request_17 | image_03 | receipt net amount | event_1545 amount |
| request_18 | message_13 | internal transfer pair | cash-neutral event relation |
| request_19 | image_04 | delivered-order total | event_1700 amount |
| request_20 | message_14 + image_05 | refund not credited; bill due | event_1785 no cash change + event_1786 amount |
| request_22 | message_15 | valuation only/no units sold | event_1960 informational/non-cash confirmation |
| request_23 | message_16 | prize processing/not credited | informational/no cash change |
| request_24 | message_17 | credited prize is one-time/closed | event_2165 one-time classification |

Contracts: exact event amount/date, recurring-stream amount/percentage/termination,
cash-state or cash-neutral clarification, one-time classification, and explicit
no-material-cash-change. Unresolved value, scope, ownership, or conflicting evidence
stays unsupported.
