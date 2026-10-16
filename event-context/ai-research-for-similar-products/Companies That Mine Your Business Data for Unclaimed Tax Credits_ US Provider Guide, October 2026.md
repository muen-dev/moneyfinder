# Companies That Mine Your Business Data for Unclaimed Tax Credits (US, October 2026)

Yes. There are real services that connect to your payroll, accounting, HR and engineering systems, find credits you haven't claimed, and prepare the claim. They fall into four groups: (1) software-led R&D credit platforms such as Neo.Tax, Boast, MainStreet (now owned by Employer.com), Arvo/Clarus R+D and Gusto's built-in credit service; (2) payroll and HR data giants that screen every new hire for hiring credits (ADP SmartCompliance, Equifax Workforce Solutions, Experian Employer Services); (3) specialty consulting and engineering firms that cover the broader menu of credits (alliantgroup, Leyton, Engineered Tax Services, KBKG, Source Advisors); and (4) large accounting firms. Which one fits depends mainly on two things: which credit you are after, since R&D, hiring credits and real-estate/energy incentives each have their own specialists, and whether you want a flat fee or are willing to give up 15–35% of the refund.

## TL;DR
- **For startups and SMBs with engineers**, software-plus-expert R&D platforms are the most efficient route. Neo.Tax charges a flat subscription (never a percentage of the credit) and builds the study from Jira, GitHub and payroll. Boast charges a success fee of typically 15–25% and includes audit support. Gusto users can claim and apply the R&D payroll offset inside payroll. Pre-revenue startups can apply up to $500K a year of the credit against payroll taxes.
- **For hourly-heavy employers**, ADP, Equifax and Experian screen new hires for the Work Opportunity Tax Credit (WOTC) and state/local incentives through your applicant-tracking and onboarding systems. WOTC lapsed for hires starting on or after January 1, 2026 and is awaiting reauthorization by Congress. Keep filing Form 8850 within 28 days of each hire so you're covered if Congress extends it retroactively.
- **2026 timing matters.** The retroactive Section 174A window for small businesses closed July 6, 2026. The Employee Retention Credit (ERC) is closed to new claims and under heavy enforcement. R&D refund claims must include the IRS's "five items of information" (with a correction window through January 10, 2027). Choose providers that document at the project ("business component") level, give you a written fee, and defend their work on audit. Avoid anyone selling "free money" on contingency with no documentation.

## Comparison Table

| Provider | Type | Main credits | Data it pulls | Fee model (public) | Best for | Key signal / flag |
|---|---|---|---|---|---|---|
| **Neo.Tax** (neo.tax) | AI software + tax experts | Federal/state R&D (§41), ASC 350-40 capitalization | Jira, GitHub, payroll, accounting via API | Flat annual subscription by R&D headcount plus implementation fee; "never a percentage of the credit" | Mid-market/enterprise; ONESOURCE users | Thomson Reuters ONESOURCE partner; raised $12M in March 2025; no public price |
| **Boast** (boast.ai) | AI platform + in-house specialists | US R&D + Canadian SR&ED | Dev tools (GitHub, Jira, GitLab), ERPs, payroll | Success fee, "generally between 15 and 25%" of credit | Tech startups to mid-market, US/Canada | Founded 2011; 1,700+ clients, $625M+ claimed; audit support included |
| **MainStreet** (now under Employer.com) | SaaS credit finder | R&D, retirement plan, health, disability/accessibility credits | Payroll/HR (via Finch: Gusto, ADP, Rippling, etc.), accounting, questionnaire | Historically 20% of savings; current pricing not clearly published | Startups/SMBs | Acquired May 2025; brand merged with Bench; product status in flux |
| **Gusto R&D Tax Credit Services** (gusto.com) | Payroll-embedded | R&D, retirement plan startup, FICA tip credits | Gusto payroll data, Codat accounting import | Service fee; real-time payroll offset free if you file through Gusto, $100/mo if filed elsewhere | Gusto customers, small businesses | Applies the R&D payroll offset directly in payroll |
| **Arvo (Clarus R+D)** (clarusrd.com) | Software + experts | Federal/state R&D | Payroll integrations, GitHub, Jira | Startups: base fee + % of credit; enterprise: fixed price | SMBs, CPA firms | Owned by TriNet 2022–25, sold to Arvo Tech March 2025\[1\]\[2\] |
| **ADP SmartCompliance Tax Credits** (adp.com) | Payroll giant | WOTC, R&D, hiring/training, location incentives, economic development | ADP payroll, ATS (e.g., Oracle Recruiting), hiring data | Quote-based | Mid-market/enterprise with steady hiring | Database of ~3,000 programs and 1,800 zones; "$6B+ since 2017"\[3\]\[4\] |
| **Equifax Workforce Solutions** (workforce.equifax.com) | Data/HR services | WOTC, disaster credits, hiring incentives | Onboarding/new-hire packets, payroll file | Quote-based | High-volume hourly employers | Long-running WOTC processor; also white-labeled through isolved |
| **Experian Employer Services** (experian.com/employer-services) | Data/HR services | WOTC, R&D, sales/use tax incentives, disaster zone, FMLA credit (45S), ERC | ATS/HCM (Workday-certified), payroll | Quote-based | Enterprise/high-volume hiring | 14M+ WOTC screenings a year; $1B+ in credits secured\[5\] |
| **alliantgroup** (alliantglobal.com) | Specialty consulting (CPA-referral model) | R&D, cost segregation, 179D, other incentives | Interviews, project and payroll records | Not public; historically reported at 25–35% | SMB/mid-market through CPA firms | IRS criminal probe (2022) closed with no action in February 2026; long history of fee disputes and mixed Tax Court record |
| **Leyton USA** (leyton.com/us) | Global consultancy | R&D, orphan drug, 45L, 179D, cost seg, SALT, sales/use tax refunds, utility exemptions, grants | Interviews, accounting, technical docs | Contingency ("if no credit is identified, there will be no cost") | SMB to enterprise | 5,000+ staff globally; ERC-era fee disputes and negative Trustpilot reviews |
| **Engineered Tax Services** (engineeredtaxservices.com) | Licensed engineering firm | Cost segregation, 179D, 45L, R&D, "Engineered Incentives Reports" | Property and construction docs, site visits | Quote; cost seg studies reported at about $3K–$12K | Real-estate owners, A/E firms, developers | Says it performs 10,000+ studies a year\[6\] |
| **KBKG** (kbkg.com) | Specialty firm + software | R&D (with audit defense), cost seg, 179D, 45L, ERC, transfer pricing, IC-DISC, state incentives | CPA-supplied data, Dash.tax software | Not published | CPA firms, larger companies; Dash.tax for small R&D claims | Dash.tax handles small claims (up to $50K in R&D credits), white-labeled for CPAs |
| **Source Advisors** (sourceadvisors.com) | Specialty firm + software | R&D/§174, cost seg, 179D, 45L, ITC/PTC, LIFO, sales/use and property tax | Payroll/accounting (GOAT.tax), engineering review | Not published; free assessment | CPA-referred mid-market; GOAT.tax for small businesses | 40-year history; defends cost seg work on exam at no charge\[7\] |

## Details: How Each Provider Works

### Software-led R&D credit platforms

**Neo.Tax.** Neo.Tax's AI reads Jira, GitHub and payroll data and produces an audit-ready R&D study "in days," with no engineer surveys or interviews. It ties every dollar of qualified expenses to a specific ticket and person. The company says AI classifies projects and drafts narratives, but the credit calculation itself (qualified-expense totals, the §280C election and Form 6765 Section G) comes from a rules-based engine.\[8\] That design helps with the IRS's new requirement to report by business component. It also connects through API to payroll, project-management and accounting systems and files Form 6765 inside Thomson Reuters ONESOURCE.\[9\] Pricing is a flat annual subscription tiered by how many employees do R&D, plus a one-time implementation fee, and is "never a percentage of the credit."\[8\] Earlier listings showed startup pricing (from $800 a year, or 2% of qualified expenses), but the company has since moved upmarket.\[10\]\[11\] A July 2026 competitor review notes the site now targets enterprises (citing Adobe and Capital One) and has no startup pricing.\[12\] The company was founded by a Stanford machine-learning PhD and a former IRS agent, and CB Insights records a $12M raise in March 2025.\[9\]\[13\] **Verdict:** the most defensible documentation model of the group for companies that already track work in Jira or GitHub. It is no longer a self-serve startup tool.

**Boast.** Boast was founded in 2011 and combines an AI classifier with in-house technical and tax specialists.\[14\]\[15\] It connects to dev tools (GitHub, Jira, GitLab) and ERPs, scores activities for eligibility, writes the technical narratives and files claims.\[12\] It covers US federal and state R&D credits and Canadian SR&ED. Its fee is success-based: "We only get paid when you receive R&D tax credits… generally between 15 and 25% of the credit obtained."\[14\] It markets AuditShield audit representation at no extra cost.\[12\] Its own figures: more than 1,700 businesses served and over $625 million accessed.\[15\] Boast claims its fees run 40–60% below "Big 6" firms.\[16\] That is its own marketing claim and has not been independently verified. **Verdict:** a reasonable full-service choice for US/Canadian tech companies. Because the fee is a percentage, it gets expensive for large claims.\[17\]

**MainStreet (Employer.com).** MainStreet was founded in 2019.\[18\] It popularized the "connect your Gusto in two minutes" model: it pulled payroll and HR data through Finch's unified API (Gusto, ADP, TriNet, Justworks and others) and checked monthly against "200+" federal, state and local credits. It took a flat 20% success fee and at one point advanced 80% of a found credit upfront.\[18\]\[19\] According to TechCrunch, it raised $60M in March 2021 in a SignalFire-led round at a $500M post-money valuation, bringing total funding to about $64.7M (a later TechCrunch piece puts it at about $75M). In 2022 it cut 30% of staff and raised a down round at a $200M valuation. Employer.com acquired it on May 5, 2025, saying MainStreet had helped "thousands of companies claim over $200M in tax savings."\[20\] In August 2025 Employer.com folded Bench Accounting and other acquisitions into a single "Mainstreet" brand.\[21\] The current mainstreet.ai site markets R&D, retirement-plan, small-business health and disabled-access credits with "documentation your CPA can file."\[22\] A competitor (Claimship) reports that the original credit marketing site was replaced as of July 2026 while the customer dashboard still runs.\[23\] **Verdict:** real and still operating, but ownership and product changes make it important to get current pricing, audit-support terms and staffing in writing before you sign.

**Gusto.** For Gusto payroll customers, Gusto's "proprietary software can identify eligible Research & Development, Retirement Plan, and FICA Tip tax credits." Gusto says it helped businesses unlock over $64M in credits in a single year.\[24\] Its key advantage is mechanical. Qualified small businesses can apply the R&D credit against payroll taxes inside Gusto through real-time or quarterly redemption. Real-time redemption is free if you use Gusto's R&D service and $100 a month if a third party prepared your claim.\[25\] Accounting data comes in through a Codat integration, or you can enter it by category.\[26\] **Verdict:** the lowest-friction option for small Gusto shops with straightforward R&D. Less suited to complex multi-entity or multi-state claims.

**Arvo Tech / Clarus R+D.** Clarus was founded in Columbus in 2016. It had served more than 1,400 customers and claimed over $135M by early 2022.\[27\]\[28\] TriNet bought it in September 2022 and sold it to Arvo Tech on March 6, 2025, with a five-year agreement to keep serving TriNet customers.\[1\]\[29\]\[30\] The platform connects to GitHub and Jira, runs both the regular and simplified credit calculations automatically, and produces Form 6765 and supporting documentation.\[28\]\[31\]\[32\] Pricing: startups pay "a small base fee plus a percentage of their credit," and enterprise customers pay a fixed price.\[33\] It also serves CPA firms that want to offer R&D studies themselves.\[32\] **Verdict:** solid for SMBs and accountants. Get the percentage in writing.

**Newer flat-fee entrants.** Claimship (flat $1,500–$3,000 a year; GitHub, Jira, Linear, Rippling, Gusto integrations) and Fondo (startup accounting that includes R&D credits, with a Gusto integration) are aimed at startups.\[23\]\[34\] They have short track records. Most comparison articles on these tools are written by the vendors themselves, so treat them as marketing.

### Payroll and HR data providers: hiring credits at scale

**ADP SmartCompliance Tax Credits.** ADP checks a client's data against a proprietary database of about 3,000 credit and incentive programs and 1,800 government-designated zones. It covers WOTC, R&D, hiring and training credits, location-based and negotiated incentives, transferable credits and disaster relief, plus "retroactive reviews."\[3\]\[35\] WOTC screening is built into the hiring workflow, including an Oracle Cloud Recruiting integration.\[36\] ADP's experts submit eligibility forms to state agencies and calculate the credits. Its Economic Development Services team negotiates incentives when you expand or relocate.\[37\] ADP says it has helped clients capture more than $6 billion since 2017.\[4\] **Verdict:** strongest for multi-state employers with high hiring volume and expansion plans.

**Equifax Workforce Solutions.** Equifax adds a WOTC questionnaire to new-hire packets (Forms HQ). Its "SmartScreening" logic is designed to stop applicants from wrongly disqualifying themselves,\[38\] and it uses e-signatures to meet the 28-day Form 8850 deadline.\[39\] Equifax also handles state agency filings and provides compliance documentation.\[38\] Its WOTC service is white-labeled by HCM vendors such as isolved, which quotes credits of $1,200–$9,600 per qualifying hire.\[40\] **Verdict:** a mature, high-volume WOTC engine.

**Experian Employer Services.** Experian manages WOTC, ERC, R&D, sales and use tax incentives, disaster-zone credits and the FMLA (§45S) credit.\[41\] It runs more than 14 million WOTC screenings a year and has a Workday-certified real-time WOTC integration. It says its WOTC solution "has secured over $1 billion in tax credits."\[5\] It also handles audit preparation and credit forecasting.\[42\] **Verdict:** a good fit for enterprises on Workday or iCIMS that want hiring credits and some broader credit coverage from one vendor.

### Specialty consulting and engineering firms

**alliantgroup (Houston).** alliantgroup is one of the largest specialty tax firms working through CPA referrals.\[43\]\[44\] It covers R&D, cost segregation, 179D and other incentives, and employs former IRS and Senate tax staff.\[45\]\[46\]\[47\] Treat it with caution. IRS Criminal Investigation raided its headquarters on May 20, 2022, and grand-jury subpoenas sought CPA-referral client records covering R&D, cost segregation and 179D back to 2011.\[45\]\[48\]\[49\]\[50\] According to the firm (reported by Bloomberg Tax and Accounting Today in February 2026), that investigation was closed "with no action taken."\[48\]\[51\] Its court record is mixed. It has wins, including Populous (2020)\[47\] and an agriculture R&D ruling it announced in February 2026.\[52\] It also had a notable loss in *Phoenix Design Group*: in a December 23, 2024 opinion by Judge Travis A. Greaves, the Tax Court tested 3 sample projects out of the 238 claimed and found no qualified research in any of them, which triggered the agreed 20% §6662 accuracy-related penalty (Bloomberg Law reported $553,577 in deficiencies and penalties). It has also faced years of client fee disputes and lawsuits.\[48\] One much-cited complaint site describes fees of 25–35%, but that is not an authoritative source.\[50\]\[53\] **Verdict:** a real, operating firm with deep technical bench. Insist on a capped, written fee and a clear audit-defense commitment.

**Leyton USA.** Leyton is part of a French-founded global consultancy (est. 1997, 5,000+ staff) with US offices in Boston, New York, San Francisco, Houston and Phoenix.\[54\]\[55\] It covers federal and state R&D, orphan drug credits, 45L, 179D, cost segregation, SALT, sales and use tax refunds, utility sales-tax exemptions, property tax and grants.\[56\] Its process starts with an Initial Assessment ("If no credit is identified, there will be no cost"), then moves to data collection, technical interviews, filing and carryforward planning.\[57\] Flags: a law firm advertises that it defeated a Leyton USA fee lawsuit over an ERC claim it says was barred because the same wages were covered by PPP forgiveness.\[54\] US-branch Trustpilot reviews include complaints about owing fees regardless of outcome.\[58\] Both are one-sided sources. **Verdict:** wide coverage, especially strong on SALT and refund work. Read the fee and payment-trigger clauses closely.

**Engineered Tax Services (ETS).** ETS describes itself as a licensed engineering firm specializing in tax strategy. It performs more than 10,000 cost segregation, 179D and R&D studies a year, plus 45L credits and "Engineered Incentives Reports" that list every credit or deduction a business might qualify for.\[6\]\[59\] Cost segregation uses site visits aligned with the IRS Audit Techniques Guide.\[59\] A competitor puts ETS's typical cost segregation fee at $3,000–$12,000 over a 4–6 week timeline.\[60\] **Verdict:** the right kind of firm for property owners, developers and architecture/engineering firms.

**KBKG and Source Advisors.** Both work mainly through CPA firms and both now sell R&D software for smaller claims. KBKG covers R&D (including audit defense), cost segregation, 179D, 45L, ERC, transfer pricing, IC-DISC and state/location incentives.\[61\]\[62\] Its Dash.tax software, which can be white-labeled for CPAs, helps "small businesses and startups… claim up to $50,000 in R&D tax credits."\[63\] Source Advisors (Fort Worth, 40-year history) covers R&D/§174, cost segregation, 179D, 45L, ITC/PTC, LIFO and sales/use and property tax.\[7\]\[64\]\[65\] Its GOAT.tax software integrates with most payroll and accounting systems, and it says it will defend its cost segregation work "at no charge in examination."\[66\]\[67\] Neither firm publishes fees.

**Big 4 and large accounting firms.** Deloitte, EY, KPMG, PwC, Grant Thornton, BDO, RSM and similar firms run credits-and-incentives practices for enterprise clients. These include R&D studies, negotiated location incentives and 45S/45F planning. They typically bill hourly or fixed-fee rather than contingency. They are the authoritative sources on new IRS requirements (for example, the Form 6765 alerts from Grant Thornton, BDO and KPMG).\[68\]\[69\]\[70\] **Verdict:** worth it for multi-entity, high-dollar or contested claims. Too expensive for most small businesses.

## Landscape: What Gets Missed and What Changed in 2025–2026

**Commonly missed credits:**
- The R&D credit (§41), including the payroll offset for qualified small businesses with under $5M in gross receipts and no receipts before the five-year window. Up to $500K a year can go against payroll taxes, capped at $250K against each tax type.\[71\]\[72\]
- WOTC.
- Retirement-plan startup and FICA-tip credits.\[24\]
- The small-employer health insurance credit and the disabled-access credit.\[22\]
- §45S paid leave and §45F child care.
- Energy and real estate incentives: 179D, 45L and cost segregation.
- State and local hiring, zone and training incentives.
- Sales and use tax refunds.

**R&D refund claims.** Any amended-return claim for the research credit must include the "five items of information": every business component, the research activities, the individuals involved, the information sought, and total qualified wage, supply and contract expenses.\[73\]\[74\] The IRS currently waives the names-of-individuals and information-sought items at filing. It has also extended the 45-day "perfection" transition period through January 10, 2027.\[69\]\[75\] Form 6765 Section G (business-component detail) was optional for tax year 2025 and becomes mandatory for tax years beginning after 2025, with some small-claimant exceptions.\[69\]\[76\] The payroll-tax election cannot be made on an amended return, so startups that missed the original filing lose the payroll offset for that year.\[77\]\[78\]

**Section 174A (OBBBA, signed July 4, 2025).** The law restored immediate expensing of domestic R&E costs from 2025 onward. Small businesses with average gross receipts of $31M or less could amend their 2022–2024 returns under Rev. Proc. 2025-28. **That window closed July 6, 2026.**\[75\]\[79\] What is still available: deducting the remaining unamortized 2022–2024 balance on the 2025 return or splitting it across 2025 and 2026, and §41 claims for years still open.\[80\]\[81\] Many states have not conformed.\[82\] Treat any provider still pitching "174 retroactive refunds" in late 2026 as a red flag.

**ERC.** OBBBA barred Q3/Q4 2021 claims filed after January 31, 2024 and extended the IRS's ERC audit window to six years.\[83\] As of the week ending October 3, 2026, the IRS reports about 13,000 claims still pending: 750 under review, 2,300 pending payment or disallowance, 3,000 under audit, 5,400 awaiting review of disallowance responses and 1,500 in Appeals. The withdrawal program is still open for claims that haven't been paid, or where the check hasn't been cashed.\[84\] **No legitimate provider should be selling new ERC claims.**

**WOTC.** Authorization expired December 31, 2025.\[85\] State agencies still accept Form 8850 but mark 2026 hires as "pending" until Congress acts.\[86\]\[87\] According to SHRM, Congress has extended the program 13 times since 1996, "often retroactively"; the longest previous lapse was 13 months (2014–2015), which the December 2015 PATH Act fixed retroactively to January 1, 2015. A retroactive fix this time is still not guaranteed. Keep screening, and treat 2026 WOTC credits as possible upside, not something to budget on.

**Paid leave and child care.** OBBBA made §45S permanent and expanded it. Starting in 2026, employers can claim it on premiums paid for paid family and medical leave insurance (IRS Notice 2026-28) as well as on wages. The credit ranges from 12.5% to 25% of wages for up to 12 weeks of leave.\[88\] §45F rises from 25% to 40% of qualified spending with a $500K cap, or 50% with a $600K cap for eligible small businesses, for tax years after 2025.\[89\]\[90\] Both credits are newly valuable and few providers have built services around them yet.

**IRS promoter warnings.** The IRS's 2026 "Dirty Dozen" (IR-2026-30) warns about bogus "self-employment tax credit" promotions and social-media "tax hacks" that lead people to claim credits they don't qualify for.\[91\] Its earlier Dirty Dozen alerts covered aggressive ERC promoters (IR-2024-85) and fake fuel tax credit claims (2025).\[92\]\[93\]

## Recommendations: Choosing a Provider

1. **Match the provider to the credit.** Software-led R&D platforms (Neo.Tax, Boast, Gusto, Arvo/Clarus) for engineering-heavy companies. ADP, Equifax or Experian for hourly hiring credits. Engineering firms (ETS, KBKG, Source Advisors) for buildings and energy. A Big 4 or large regional firm for enterprise-scale or contested claims.
2. **Prefer flat or capped fees for large claims.** Contingency rates of 15–35% reward inflated claims and leave the audit risk with you. Circular 230 (31 CFR §10.27) generally bars contingent fees for work before the IRS, but a 2014 D.C. federal court ruling (*Ridgely v. Lew*) stopped the IRS from enforcing that rule against ordinary refund claims, which is why contingency offers tend to cluster around amended returns.
3. **Demand business-component documentation.** Ask for a sample deliverable that would satisfy the five-item rule and Section G. Avoid anyone whose method is "a 15-minute questionnaire and a number."
4. **Get audit defense in writing.** Confirm who represents you, at what cost, and whether fees are refunded if credits are disallowed.
5. **Check the payment trigger.** Find out whether you pay when the claim is filed, when the refund arrives, or when the credit is used. The Leyton and alliantgroup fee disputes centered on exactly this.
6. **Look out for warning signs.** Pitches for new ERC claims, 2022–2024 §174 refunds after July 6, 2026, guaranteed refund amounts, pressure to sign quickly, or a refusal to let your own CPA review the claim.

## Caveats
- Several pricing figures come from third-party review sites or competitor comparison pages (Claimship, Cost Seg Smart, GetApp/Capterra), not the vendors. Confirm current quotes directly.
- Company-reported totals (for example, ADP's $6B, Boast's $625M, Experian's $1B) are self-reported marketing figures and have not been independently verified.\[4\]\[5\]
- MainStreet's product status after its acquisition and Neo.Tax's shift to enterprise customers are still changing.
- WOTC reauthorization, IRS ERC processing and Form 6765 rules may change after October 2026.
- This report describes providers. It is not tax advice.

## Sources

1. [Arvo Tech Acquires TriNet Clarus R+D](https://www.privsource.com/acquisitions/deal/arvo-tech-acquires-trinet-clarus-r-d-zqSojJ)
2. [TriNet Acquires Clarus R+D Solutions LLC](https://www.privsource.com/acquisitions/deal/trinet-acquires-clarus-r-d-solutions-llc-x7S486)
3. [Features](https://apps.adp.com/en-US/apps/29723/adp-smartcompliance-tax-credits/features)
4. [ADP SmartCompliance® Tax Credits](https://apps.adp.com/en-US/apps/29723/ADP%20SmartCompliance%C2%AE%20Tax%20Credits/features)
5. [Experian secures Workday Certified Integration for its Work Opportunity Tax Credit solution](https://www.experian.com/employer-services/resources/news/experian-secures-workday-certified-integration-for-its-wotc-solution)
6. [Engineered Tax Services](https://engineeredtaxservices.com/)
7. [Top Cost Segregation Providers in 2026: Ranked & Compared](https://www.senecacostseg.com/feeds/blog/compare-pricing-cost-segregation-services)
8. [R&D Tax Credit, without surveys or interviews.](https://www.neo.tax/compare)
9. [ONESOURCE + Neo.Tax: Eliminating the triple burden of R&D credit compliance](https://tax.thomsonreuters.com/blog/neo-tax-onesource-eliminating-the-triple-burden-of-rd-credit-compliance/)
10. [neo.tax Software Pricing, Alternatives & More 2026](https://www.capterra.com/p/227621/neotax/)
11. [neo.tax Reviews, Prices & Ratings](https://www.getapp.co.uk/software/2048924/neo-tax)
12. [Best R&D Tax Credit Software for Startups (2026) - Claimship](https://www.claimship.com/best-rd-tax-credit-software)
13. [Compare CrossBorder Solutions vs Neo.Tax](https://www.cbinsights.com/compare/crossborder-solutions-vs-neotax)
14. [R&D Tax Credit FAQ - Boast.AI](https://www.boast.ai/en-us/rd-tax-credit-faqs)
15. [Founded Year](https://www.cbinsights.com/investor/boast)
16. [Solutions for Federal and State R&D Tax Credits by Industry, Size, and Role](https://www.boast.ai/en-us/platform-comparison)
17. [Boast.ai Review 2026: R&D Tax Credits, Pricing, Integrations, and Coverage](https://www.hr.software/reviews/boast-ai)
18. [New Startup Highlight: MainStreet - Finovate](https://finovate.com/new-startup-highlight-mainstreet/)
19. [MainStreet and Finch — A match made in tax credit heaven](https://www.tryfinch.com/customer-stories/mainstreet-and-finch-a-match-made-in-tax-credit-heaven)
20. [Employer.com Acquires MainStreet To Expand SMB Back Office Solutions](https://www.wjhl.com/business/press-releases/ein-presswire/808900070/employer-com-acquires-mainstreet-to-expand-smb-back-office-solutions/)
21. [Employer.com Rebrands and Streamlines With Mainstreet](https://www.einpresswire.com/article/838170679/employer-com-rebrands-and-streamlines-with-mainstreet)
22. [MainStreet R&D Tax Credits for Small Business](https://mainstreet.ai/)
23. [MainStreet Alternative for the R&D Credit](https://www.claimship.com/vs/mainstreet)
24. [Gusto](https://gusto.com/product/payroll/tax-credits)
25. [Gusto](https://gusto.com/accountants/r-and-d-tax-credit-service)
26. [Gusto Help Center- Calculate R&D tax credits with Gusto](https://support.gusto.com/article/197779649100000/calculate-rd-tax-credits-with-gusto)
27. [Clarus R+D Introduces R&D Tax Credit Platform for ALL](https://finance.yahoo.com/news/clarus-r-d-introduces-r-110000746.html)
28. [Clarus R+D Introduces R&D Tax Credit Platform for ALL](https://www.globenewswire.com/news-release/2022/01/11/2364612/0/en/Clarus-R-D-Introduces-R-D-Tax-Credit-Platform-for-ALL.html)
29. [Arvo Tech Acquires Clarus R+D Solutions](https://mergr.com/transaction/arvo-tech-acquires-clarus-r+d-solutions)
30. [TriNet Group (TNET) Sells Clarus R+D to Arvo Tech](<https://www.streetinsider.com/Corporate+News/TriNet+Group+(TNET)+Sells+Clarus+R+D+to+Arvo+Tech/24462938.html>)
31. [R&D Tax Credit Software & Consulting Services](https://clarusrd.com/rd-tax-credit/)
32. [\- Tax Technology Product By R&D Tax Credit Solution](https://www.taxtech500.com/products/536)
33. [Contact Tax Credit Experts](https://clarusrd.com/contact/)
34. [The Most Efficient Software For Claiming The R&D Payroll Tax Offset That Pulls Real-Time Employee Wage Data Directly From Gusto](https://fondo.com/blog/the-most-efficient-software-for-claiming-the-r-d-payroll-tax-offset-that-pulls-real-time-employee-wage-data-directly-from-gusto)
35. [ADP SmartCompliance® Tax Credits](https://apps.adp.com/en-US/apps/29723/ADP%20SmartCompliance%C3%82%C2%AE%20Tax%20Credits/features)
36. [ADP Tax Credits for Oracle Recruiting](https://marketplace.oracle.com/listings/72654125)
37. [ADP SmartCompliance® Tax Credits](https://apps.adp.com/en/apps/29723/adp-smartcompliance-tax-credits/features)
38. [Work Opportunity Tax Credit Management](https://workforce.equifax.com/solutions/work-opportunity-tax-credit-management)
39. [Equifax Workforce Solutions Enhances WOTC Eligibility Screening with eSignature](https://www.prnewswire.com/news-releases/equifax-workforce-solutions-enhances-wotc-eligibility-screening-with-esignature-176752771.html)
40. [WOTC Software for Capturing Work Opportunity Tax Credits](https://www.isolvedhcm.com/talent-acquisition/employee-onboarding/wotc)
41. [About](https://www.experian.com/employer-services/about)
42. [Experian WOTC Integration](https://essiumlabs.com/integrations/experian-wotc-tracking/)
43. [alliantgroup - Products, Competitors, Financials, Employees, Headquarters Locations](https://www.cbinsights.com/company/alliantgroup)
44. [Associate Attorney](https://builtin.com/job/associate-attorney/7458893)
45. [CPA Firms That Referred Clients to Alliantgroup Have Been Subpoenaed, Asked to Turn Over 11 Years of Client Data - Going Concern](https://www.goingconcern.com/alliantgroup-federal-grand-jury-subpoena/)
46. [Tax Services Firm Announces Research Credit Decision Overturned](https://www.taxnotes.com/research/federal/other-documents/washington-roundup/tax-services-firm-announces-research-credit-decision-overturned/ws0l)
47. [alliantgroup Scores Another Big R&D Tax Credit Win for Taxpayers](https://www.prnewswire.com/news-releases/alliantgroup-scores-another-big-rd-tax-credit-win-for-taxpayers-301022583.html)
48. [IRS raids alliantgroup offices](https://www.accountingtoday.com/news/irs-raids-alliantgroup-offices)
49. [IRS Criminal Unit Probes Tax Consulting Firm with Vast D.C. Ties](https://news.bloombergtax.com/daily-tax-report/irs-criminal-unit-probes-tax-consulting-firm-with-vast-d-c-ties)
50. [The IRS Is Paying an Unwelcome Visit to Alliantgroup (NEW UPDATE) Experts Weigh In On Feds' Raid of the 'Blue A' - Going Concern](https://www.goingconcern.com/the-irs-is-paying-an-unwelcome-visit-to-alliantgroup/)
51. [IRS Crime Unit Ends Investigation Into Tax Firm With DC Ties](https://news.bloombergtax.com/daily-tax-report/irs-crime-unit-ends-investigation-into-tax-firm-with-dc-ties)
52. [Press Release Archives](https://alliantglobal.com/insights/category/press-release/)
53. [Alliant Group Defrauding Clients in Tax Matters Houston, Texas Houston, Texas -](https://www.ripoffreport.com/report/alliant-group/houston-texas-77056/alliant-group-defrauding-clients-in-tax-matters-houston-texas-houston-texas-757665)
54. [How We Helped a Business Defeat Leyton USA’s Improper ERTC Claim](https://vladylaw.com/attorney-leyton-ertc-debt-lawsuit/)
55. [Senior R&D Tax Credit Consultant - Leyton](https://bebee.com/us/jobs/senior-rd-tax-credit-consultant-leyton-massachusetts--theirstack-684110338)
56. [Financial Incentives & Tax Services](https://leyton.com/us/)
57. [R&D Tax Credit: What it is and How do I Claim It?](https://leyton.com/us/rd-tax-credit/)
58. [pt.trustpilot.com](https://pt.trustpilot.com/review/leyton.com/us)
59. [Cost Segregation Study Cost: 2026 Guide to Pricing and ROI](https://engineeredtaxservices.com/cost-segregation-study-cost-2026-guide-to-pricing-and-roi/)
60. [Engineered Tax Services vs Cost Seg Smart (2026 Review)](https://costsegsmart.com/compare/vs-engineered-tax-services/)
61. [KBKG - Tax Credits, Incentives & Cost Recovery](https://www.linkedin.com/company/kbkg)
62. [KBKG](https://www.kbkg.com/research-and-development/rd-tax-credit-for-software-development)
63. [Dash.tax R&D Tax Credit Software](https://www.kbkg.com/dash-tax-lp)
64. [Map - Source Advisors](https://sourceadvisors.com/map/)
65. [In-depth review of Source Advisors](https://top179dtaxlawyers.com/read-more/9)
66. [COST SEGREATION](https://sourceadvisors.com/wp-content/uploads/2024/11/Cost-Seg-Service-Page-Rev-2024-.pdf)
67. [R&D Tax Credits Platform for Businesses](https://sourceadvisors.com/rd-tax-credit/rd-tax-credit-software/)
68. [Updated Form 6765 reporting requirements](https://www.grantthornton.com/insights/alerts/tax/2025/insights/new-form-reporting-requirements)
69. [IRS Extends Transition Period for Research Credit Refund Claims, Makes Section G Optional for Tax Year 2025](https://www.bdo.com/insights/tax/irs-extends-transition-period-for-research-credit-refund-claims)
70. [tnf wnit form 6765 apr21 2025](https://kpmg.com/kpmg-us/content/dam/kpmg/taxnewsflash/pdf/2025/04/tnf-wnit-form-6765-apr21-2025.pdf)
71. [R&D Tax Credits for Software Development - Boast.ai](https://boast.ai/en-us/blog/what-to-know-about-rd-tax-credits-for-software-development/)
72. [How Can My Business Use the R&D Tax Credit?](https://gusto.com/resources/articles/taxes/r&d-tax-credit-to-offset-taxes)
73. [Research credit claims (Section 41) on amended returns frequently asked questions](https://www.irs.gov/businesses/corporations/research-credit-claims-section-41-on-amended-returns-frequently-asked-questions)
74. [How to File a Retroactive Claim for the Federal R&D Tax Credit](https://gusto.com/resources/articles/taxes/retroactive-r&d-tax-credit-claim)
75. [2026 R&D Tax Credit Field Guide: Rules and Rates](https://www.striketax.com/journal/2026-rd-tax-credit-field-guide)
76. [Form 6765, Explained: How the R&D Credit Actually Gets Claimed](https://onshore.com/learn/form-6765)
77. [FAQs About R&D Tax Credits](https://gusto.com/partner-resources/faqs-about-rd-tax-credits)
78. [Qualifying for and Claiming Your R&D Credit](https://gusto.com/partner-resources/qualifying-and-claiming-rd-credit)
79. [Rev. Proc. 2025-28 & OBBBA: R&D Tax Savings Guide](https://www.striketax.com/journal/maximize-r-d-tax-savings-with-irs-rev-proc-2025-28-and-obbba)
80. [Section 174A Amended Returns: What Happens Next](https://www.striketax.com/journal/after-the-july-6-section-174a-deadline-what-happens-next)
81. [Section 174A R&D Expensing: July 6, 2026 Retroactive](https://reedcorp.tax/helpful-guides/rd-expensing-section-174a-deadline-2026/)
82. [Section 174A: Q2 2026 Deferred Tax Reversal Guide](https://www.finrep.ai/blog/section-174a-q2-2026-deferred-tax-reversal-guide)
83. [Employee Retention Credit Update 2026: Pending Refunds, New Compliance Rules, and What to Do Next](https://beancount.io/blog/2026/04/25/employee-retention-credit-update-2026-pending-refunds-compliance-guide)
84. [Employee Retention Credit](https://www.irs.gov/coronavirus/employee-retention-credit)
85. [ADP Pushes for WOTC Screening Changes](https://tax.thomsonreuters.com/news/adp-pushes-for-wotc-screening-changes/)
86. [Home Page - eWOTC](https://webapps.dwd.state.wi.us/eWOTC/)
87. [WOTC in 2026: The Program Is in Hiatus](https://www.onemoreway.org/blog/policy/wotc-2026-hiatus/)
88. [Treasury, IRS Issue Guidance on the Permanent Expansion of Paid Family and Medical Leave under the Working Families Tax Cuts](https://www.irs.gov/newsroom/treasury-irs-issue-guidance-on-the-permanent-expansion-of-paid-family-and-medical-leave-under-the-working-families-tax-cuts)
89. [Understanding OBBB Enhancements to Employer Leave and Childcare Credits](https://tax.thomsonreuters.com/news/understanding-obbb-enhancements-to-employer-leave-and-childcare-credits/)
90. [Employer Childcare Tax Credit: 40% Rate in 2026](https://tscpatax.com/articles/employer-childcare-credit-2026)
91. [IR-2026-30: Dirty Dozen tax scams for 2026: IRS reminds taxpayers to watch out for dangerous threats](https://content.govdelivery.com/accounts/USIRS/bulletins/40cce34)
92. [IR-2024-85: Dirty Dozen: Beware of aggressive promoters who dupe taxpayers into making questionable Employee Retention Credit claims; risks continue for small businesses, special withdrawal program remains available](https://content.govdelivery.com/accounts/USIRS/bulletins/3934edb)
93. [Duane Morris LLP - Phishing, Smishing and Other Threats - IRS Releases the Dirty Dozen Tax Scams for 2025](https://www.duanemorris.com/alerts/phishing_smishing_other_threats_irs_releases_dirty_dozen_tax_scams_2025_0325.html)
