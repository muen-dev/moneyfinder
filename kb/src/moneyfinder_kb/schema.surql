-- moneyfinder knowledge base schema. Targets SurrealDB 3.x (tested on 3.3.0).
--
-- Three layers:
--   1. Lake catalog   source / document / chunk     what we fetched, from where, when; retrieval units
--   2. Tax knowledge  incentive / form / criterion  structured facts, each citing the chunks it came from
--   3. Businesses     business / eligible_for / claimed   assessments and filings per tax year
--
-- Safe to re-run (`kb init`): tables, fields and functions use OVERWRITE, indexes use IF NOT EXISTS.
-- To change an existing index definition, REMOVE INDEX it first; IF NOT EXISTS keeps the old one.

DEFINE ANALYZER OVERWRITE tax_en TOKENIZERS class FILTERS lowercase, ascii, snowball(english);


-- ─── 1. Lake catalog ────────────────────────────────────────────────────────────────

DEFINE TABLE OVERWRITE source SCHEMAFULL
    COMMENT 'A URL we track. Record id is the normalized URL. current = NONE means discovered but not fetched yet.';
DEFINE FIELD OVERWRITE url ON source TYPE string;
DEFINE FIELD OVERWRITE domain ON source TYPE string;
DEFINE FIELD OVERWRITE authority ON source
    TYPE "statute" | "regulation" | "form" | "form_instructions" | "agency_guidance" | "program_page" | "dataset" | "secondary" | "unknown"
    DEFAULT "unknown";
DEFINE FIELD OVERWRITE jurisdiction ON source TYPE option<"NYS" | "NYC" | "federal">;
DEFINE FIELD OVERWRITE agency ON source TYPE option<string>;
DEFINE FIELD OVERWRITE title ON source TYPE option<string>;
DEFINE FIELD OVERWRITE tags ON source TYPE array<string> DEFAULT [];
DEFINE FIELD OVERWRITE current ON source TYPE option<record<document>>;
DEFINE FIELD OVERWRITE first_seen_at ON source TYPE datetime DEFAULT time::now() READONLY;
DEFINE FIELD OVERWRITE last_fetched_at ON source TYPE option<datetime>;
DEFINE FIELD OVERWRITE last_error ON source TYPE option<string>;
DEFINE INDEX IF NOT EXISTS source_domain ON source FIELDS domain;
DEFINE INDEX IF NOT EXISTS source_current ON source FIELDS current;

DEFINE TABLE OVERWRITE document SCHEMAFULL
    COMMENT 'Extracted content. Record id is the sha256 of the extracted text, so an unchanged page is never re-chunked or re-embedded.';
DEFINE FIELD OVERWRITE origin ON document TYPE record<source>;
DEFINE FIELD OVERWRITE content_type ON document TYPE string;
DEFINE FIELD OVERWRITE raw_key ON document TYPE string COMMENT 'Lake key of the original bytes';
DEFINE FIELD OVERWRITE text_key ON document TYPE string COMMENT 'Lake key of the extracted markdown';
DEFINE FIELD OVERWRITE title ON document TYPE option<string>;
DEFINE FIELD OVERWRITE pages ON document TYPE option<int>;
DEFINE FIELD OVERWRITE chunk_count ON document TYPE int;
DEFINE FIELD OVERWRITE created_at ON document TYPE datetime DEFAULT time::now() READONLY;
DEFINE FIELD OVERWRITE superseded_at ON document TYPE option<datetime>
    COMMENT 'Set when the source starts serving different content. Kept for audit, excluded from search.';

DEFINE TABLE OVERWRITE fetched TYPE RELATION IN source OUT document SCHEMAFULL
    COMMENT 'Version history: which content a source served, first and last time we saw it.';
DEFINE FIELD OVERWRITE first_seen_at ON fetched TYPE datetime DEFAULT time::now() READONLY;
DEFINE FIELD OVERWRITE last_seen_at ON fetched TYPE datetime DEFAULT time::now();
DEFINE FIELD OVERWRITE http_status ON fetched TYPE int;
DEFINE FIELD OVERWRITE via ON fetched TYPE string;
DEFINE INDEX IF NOT EXISTS fetched_unique ON fetched FIELDS in, out UNIQUE;

DEFINE TABLE OVERWRITE links_to TYPE RELATION IN source OUT source SCHEMAFULL
    COMMENT 'Hyperlinks between tracked sources, with anchor text.';
DEFINE FIELD OVERWRITE anchor ON links_to TYPE option<string>;
DEFINE INDEX IF NOT EXISTS links_to_unique ON links_to FIELDS in, out UNIQUE;

DEFINE TABLE OVERWRITE chunk SCHEMAFULL
    COMMENT 'Retrieval unit. Record id is [document sha256, ordinal].';
DEFINE FIELD OVERWRITE document ON chunk TYPE record<document>;
DEFINE FIELD OVERWRITE ordinal ON chunk TYPE int;
DEFINE FIELD OVERWRITE text ON chunk TYPE string COMMENT 'Starts with the heading breadcrumb, so it embeds and matches with context';
DEFINE FIELD OVERWRITE heading ON chunk TYPE option<string>;
DEFINE FIELD OVERWRITE page ON chunk TYPE option<int>;
DEFINE FIELD OVERWRITE embedding ON chunk TYPE option<array<float>>;
DEFINE INDEX IF NOT EXISTS chunk_document ON chunk FIELDS document;
DEFINE INDEX IF NOT EXISTS chunk_fts ON chunk FIELDS text FULLTEXT ANALYZER tax_en BM25 HIGHLIGHTS;
-- 1024 = Titan Text Embeddings V2 default. Must match EMBED_DIM.
DEFINE INDEX IF NOT EXISTS chunk_vec ON chunk FIELDS embedding HNSW DIMENSION 1024 DIST COSINE TYPE F32;


-- ─── 2. Tax knowledge ───────────────────────────────────────────────────────────────

DEFINE TABLE OVERWRITE incentive SCHEMAFULL
    COMMENT 'A credit, exemption, abatement or refund program. Record id is a stable slug, e.g. incentive:excelsior_jobs.';
DEFINE FIELD OVERWRITE name ON incentive TYPE string;
DEFINE FIELD OVERWRITE kind ON incentive TYPE "credit" | "exemption" | "abatement" | "refund" | "deduction" | "grant";
DEFINE FIELD OVERWRITE jurisdiction ON incentive TYPE "NYS" | "NYC" | "federal";
DEFINE FIELD OVERWRITE agency ON incentive TYPE option<string>;
DEFINE FIELD OVERWRITE summary ON incentive TYPE option<string>;
DEFINE FIELD OVERWRITE tax_types ON incentive TYPE array<string> DEFAULT [] COMMENT 'e.g. "Article 9-A", "Article 22", "NYC UBT"';
DEFINE FIELD OVERWRITE refundable ON incentive TYPE option<bool>;
DEFINE FIELD OVERWRITE carryforward_years ON incentive TYPE option<int>;
DEFINE FIELD OVERWRITE requires_preapproval ON incentive TYPE option<bool> COMMENT 'Needs a certificate (e.g. from ESD) before it can be claimed';
DEFINE FIELD OVERWRITE status ON incentive TYPE "active" | "expired" | "unknown" DEFAULT "unknown";
DEFINE FIELD OVERWRITE available_until ON incentive TYPE option<datetime>;
DEFINE FIELD OVERWRITE benefit ON incentive TYPE option<object> FLEXIBLE COMMENT 'Rates, caps, per-employee amounts';
DEFINE FIELD OVERWRITE last_verified_at ON incentive TYPE option<datetime>;
DEFINE FIELD OVERWRITE updated_at ON incentive TYPE datetime VALUE time::now();

DEFINE TABLE OVERWRITE form SCHEMAFULL
    COMMENT 'One revision of a form. Record id is [code, tax_year], e.g. form:["CT-607", 2025].';
DEFINE FIELD OVERWRITE code ON form TYPE string;
DEFINE FIELD OVERWRITE tax_year ON form TYPE int;
DEFINE FIELD OVERWRITE title ON form TYPE option<string>;
DEFINE FIELD OVERWRITE agency ON form TYPE option<string>;
DEFINE FIELD OVERWRITE pdf ON form TYPE option<record<source>>;
DEFINE FIELD OVERWRITE instructions ON form TYPE option<record<source>>;
DEFINE FIELD OVERWRITE fields ON form TYPE array<object> FLEXIBLE DEFAULT [] COMMENT 'Line items for the form-filling agent: {line, label, type, required}';
DEFINE FIELD OVERWRITE updated_at ON form TYPE datetime VALUE time::now();

DEFINE TABLE OVERWRITE criterion SCHEMAFULL
    COMMENT 'One eligibility rule for an incentive, in words and, when possible, as a machine-checkable rule.';
DEFINE FIELD OVERWRITE incentive ON criterion TYPE record<incentive>;
DEFINE FIELD OVERWRITE kind ON criterion
    TYPE "industry" | "location" | "entity_type" | "employment" | "wages" | "investment" | "certification" | "timing" | "other";
DEFINE FIELD OVERWRITE text ON criterion TYPE string;
DEFINE FIELD OVERWRITE rule ON criterion TYPE option<object> FLEXIBLE COMMENT 'e.g. {naics_prefix: ["3254"]} or {min_new_jobs: 5}';
DEFINE FIELD OVERWRITE required ON criterion TYPE bool DEFAULT true;
DEFINE INDEX IF NOT EXISTS criterion_incentive ON criterion FIELDS incentive;

DEFINE TABLE OVERWRITE uses_form TYPE RELATION IN incentive OUT form SCHEMAFULL;
DEFINE FIELD OVERWRITE role ON uses_form TYPE "claim" | "application" | "certification" | "schedule" DEFAULT "claim";
DEFINE INDEX IF NOT EXISTS uses_form_unique ON uses_form FIELDS in, out UNIQUE;

DEFINE TABLE OVERWRITE cites TYPE RELATION IN incentive | criterion | form OUT chunk SCHEMAFULL
    COMMENT 'Provenance: the chunks a structured fact was taken from.';
DEFINE FIELD OVERWRITE quote ON cites TYPE option<string>;
DEFINE FIELD OVERWRITE created_at ON cites TYPE datetime DEFAULT time::now() READONLY;
DEFINE INDEX IF NOT EXISTS cites_unique ON cites FIELDS in, out UNIQUE;


-- ─── 3. Businesses ──────────────────────────────────────────────────────────────────

DEFINE TABLE OVERWRITE business SCHEMAFULL;
DEFINE FIELD OVERWRITE name ON business TYPE string;
DEFINE FIELD OVERWRITE website ON business TYPE option<string>;
DEFINE FIELD OVERWRITE naics ON business TYPE array<string> DEFAULT [];
DEFINE FIELD OVERWRITE entity_type ON business TYPE option<"c_corp" | "s_corp" | "partnership" | "llc" | "sole_prop" | "nonprofit">;
DEFINE FIELD OVERWRITE county ON business TYPE option<string>;
DEFINE FIELD OVERWRITE nyc_borough ON business TYPE option<"Manhattan" | "Brooklyn" | "Queens" | "Bronx" | "Staten Island">;
DEFINE FIELD OVERWRITE employees ON business TYPE option<int>;
DEFINE FIELD OVERWRITE annual_revenue ON business TYPE option<decimal>;
DEFINE FIELD OVERWRITE profile ON business TYPE object FLEXIBLE DEFAULT {} COMMENT 'Whatever the research agents learn: BBB rating, Apollo description, ...';
DEFINE FIELD OVERWRITE sources ON business TYPE array<record<source>> DEFAULT [];
DEFINE FIELD OVERWRITE updated_at ON business TYPE datetime VALUE time::now();

DEFINE TABLE OVERWRITE eligible_for TYPE RELATION IN business OUT incentive SCHEMAFULL
    COMMENT 'Latest assessment of one business against one incentive for one tax year.';
DEFINE FIELD OVERWRITE tax_year ON eligible_for TYPE int;
DEFINE FIELD OVERWRITE status ON eligible_for TYPE "likely" | "possible" | "needs_info" | "ineligible";
DEFINE FIELD OVERWRITE confidence ON eligible_for TYPE option<float> ASSERT $value = NONE OR ($value >= 0 AND $value <= 1);
DEFINE FIELD OVERWRITE reasons ON eligible_for TYPE array<string> DEFAULT [];
DEFINE FIELD OVERWRITE missing_info ON eligible_for TYPE array<string> DEFAULT [];
DEFINE FIELD OVERWRITE evidence ON eligible_for TYPE array<record<chunk>> DEFAULT [];
DEFINE FIELD OVERWRITE estimated_value ON eligible_for TYPE option<decimal>;
DEFINE FIELD OVERWRITE assessed_by ON eligible_for TYPE option<string>;
DEFINE FIELD OVERWRITE assessed_at ON eligible_for TYPE datetime VALUE time::now();
DEFINE INDEX IF NOT EXISTS eligible_for_unique ON eligible_for FIELDS in, out, tax_year UNIQUE;

DEFINE TABLE OVERWRITE claimed TYPE RELATION IN business OUT incentive SCHEMAFULL
    COMMENT 'A claim drafted or filed for a tax year; status tracks it through to payment.';
DEFINE FIELD OVERWRITE tax_year ON claimed TYPE int;
DEFINE FIELD OVERWRITE status ON claimed TYPE "drafted" | "filed" | "accepted" | "paid" | "denied";
DEFINE FIELD OVERWRITE amount ON claimed TYPE option<decimal>;
DEFINE FIELD OVERWRITE form ON claimed TYPE option<record<form>>;
DEFINE FIELD OVERWRITE updated_at ON claimed TYPE datetime VALUE time::now();
DEFINE INDEX IF NOT EXISTS claimed_unique ON claimed FIELDS in, out, tax_year UNIQUE;


-- ─── Functions (callable from any client, including the SurrealDB MCP server) ──────

-- Hybrid retrieval: BM25 full-text fused with vector KNN by reciprocal rank fusion.
-- Pass $embedding = NONE for full-text only. Full-text uses OR so natural-language questions match.
-- Superseded page versions are skipped.
DEFINE FUNCTION OVERWRITE fn::search_chunks($q: string, $embedding: option<array<float>>, $k: int) {
    LET $ft = SELECT id, search::score(1) AS ft_score FROM chunk
        WHERE text @1,OR@ $q AND document.superseded_at = NONE ORDER BY ft_score DESC LIMIT 50;
    LET $vs = IF $embedding != NONE {
        SELECT id, vector::distance::knn() AS distance FROM chunk
            WHERE embedding <|50,100|> $embedding AND document.superseded_at = NONE ORDER BY distance
    } ELSE { [] };
    LET $fused = search::rrf([$vs, $ft], $k, 60);
    RETURN SELECT
        id AS chunk,
        rrf_score AS score,
        id.text AS text,
        id.heading AS heading,
        id.page AS page,
        id.document.origin.url AS url,
        id.document.origin.authority AS authority,
        id.document.title AS title,
        id<-cites<-incentive.name AS incentives
    FROM $fused ORDER BY score DESC;
};

-- Incentives a business likely qualifies for but has not claimed for the tax year.
DEFINE FUNCTION OVERWRITE fn::missed_opportunities($business: record<business>, $tax_year: int) {
    LET $claimed = SELECT VALUE out FROM claimed WHERE in = $business AND tax_year = $tax_year AND status != "denied";
    RETURN SELECT
        out AS incentive,
        out.name AS name,
        status,
        confidence,
        estimated_value,
        reasons,
        missing_info,
        evidence.{ chunk: id, url: document.origin.url } AS evidence
    FROM eligible_for
    WHERE in = $business AND tax_year = $tax_year AND status IN ["likely", "possible"] AND out NOTINSIDE $claimed
    ORDER BY confidence DESC;
};
