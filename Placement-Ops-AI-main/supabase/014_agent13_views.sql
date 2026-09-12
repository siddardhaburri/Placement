-- ============================================================
-- Agent 13 — Deterministic SQL Views (Phase 2 & Phase 3)
-- Deterministic Talent Intelligence & Opportunity/Faculty Matching Engine
-- ============================================================

CREATE SCHEMA IF NOT EXISTS outcomes;

-- ============================================================
-- 1. DETERMINISTIC STUDENT STRENGTH PROFILE & GROWTH (PHASE 2)
-- Calculates 5-domain scores, actual relative semester growth,
-- evidence counts, and relative hidden talent.
-- ============================================================
CREATE OR REPLACE VIEW outcomes.v_student_strength_profile AS
WITH 
-- 1. Resume Claims Aggregation per Student & Domain
resume_agg AS (
    SELECT 
        student_id,
        domain,
        SUM(CASE 
            WHEN verification_status = 'VERIFIED' THEN 50.0 
            WHEN verification_status = 'PENDING' THEN 15.0 -- 0.30 weight of 50.0
            ELSE 0.0 
        END) AS resume_score,
        COUNT(CASE WHEN verification_status = 'VERIFIED' THEN 1 END) AS verified_count,
        COUNT(CASE WHEN verification_status = 'PENDING' THEN 1 END) AS pending_count
    FROM studentlife.resume_claim
    GROUP BY student_id, domain
),

-- 2. Overall Evidence Counts per Student
student_evidence_counts AS (
    SELECT 
        s.id AS student_id,
        (
            SELECT COUNT(*) 
            FROM jsonb_each_text(NULLIF(s.semester_marks::jsonb, 'null'::jsonb))
            WHERE value ~ '^[0-9]+(\.[0-9]+)?$'
        ) AS academic_evidence_count,
        (
            COALESCE(jsonb_array_length(NULLIF(s.projects::jsonb, 'null'::jsonb)), 0) +
            COALESCE(jsonb_array_length(NULLIF(s.hackathons::jsonb, 'null'::jsonb)), 0) +
            COALESCE(jsonb_array_length(NULLIF(s.internship_history::jsonb, 'null'::jsonb)), 0)
        ) AS achievement_evidence_count,
        COALESCE(jsonb_array_length(NULLIF(s.certifications::jsonb, 'null'::jsonb)), 0) AS certification_evidence_count,
        COALESCE(SUM(r.verified_count), 0) AS resume_verified_count,
        COALESCE(SUM(r.pending_count), 0) AS resume_pending_count
    FROM public.students s
    LEFT JOIN resume_agg r ON s.id = r.student_id
    GROUP BY s.id, s.semester_marks, s.projects, s.hackathons, s.internship_history, s.certifications
),

-- 3. Academic Semester Growth Analysis
sem_analysis AS (
    SELECT 
        s.id AS student_id,
        sec.academic_evidence_count,
        (sec.academic_evidence_count >= 2) AS has_sufficient_history,
        CASE WHEN sec.academic_evidence_count >= 2 THEN
            (
                SELECT AVG(value::numeric) 
                FROM jsonb_each_text(NULLIF(s.semester_marks::jsonb, 'null'::jsonb))
                WHERE key IN ('sem3', 'sem4', 'sem5', 'sem6', 'sem7', 'sem8') AND value ~ '^[0-9]+(\.[0-9]+)?$'
            ) -
            (
                SELECT AVG(value::numeric) 
                FROM jsonb_each_text(NULLIF(s.semester_marks::jsonb, 'null'::jsonb))
                WHERE key IN ('sem1', 'sem2') AND value ~ '^[0-9]+(\.[0-9]+)?$'
            )
        ELSE NULL END AS raw_growth
    FROM public.students s
    JOIN student_evidence_counts sec ON s.id = sec.student_id
),

-- 4. Cohort Relative Growth Percentile & Bucket
growth_percentiles AS (
    SELECT 
        s.id AS student_id,
        sa.raw_growth,
        sa.has_sufficient_history,
        CASE WHEN sa.has_sufficient_history AND sa.raw_growth IS NOT NULL THEN
            PERCENT_RANK() OVER (PARTITION BY s.branch ORDER BY sa.raw_growth)
        ELSE NULL END AS growth_percentile
    FROM public.students s
    JOIN sem_analysis sa ON s.id = sa.student_id
),

-- 5. Domain Component Calculations (0 - 100 for each component)
domain_components AS (
    SELECT 
        s.id AS student_id,
        s.branch,
        s.cgpa,
        d.domain,
        -- Academic component (0 - 100)
        LEAST(COALESCE(s.cgpa * 10.0, 0.0), 100.0) AS academic_component,
        -- Achievement component per domain (0 - 100)
        CASE 
            WHEN d.domain = 'TECHNICAL' THEN
                LEAST(
                    (COALESCE(jsonb_array_length(NULLIF(s.projects::jsonb, 'null'::jsonb)), 0) * 25.0) +
                    (COALESCE(jsonb_array_length(NULLIF(s.hackathons::jsonb, 'null'::jsonb)), 0) * 20.0),
                    100.0
                )
            WHEN d.domain = 'RESEARCH' THEN
                LEAST(
                    (COALESCE(jsonb_array_length(NULLIF(s.projects::jsonb, 'null'::jsonb)), 0) * 20.0) +
                    (COALESCE(jsonb_array_length(NULLIF(s.internship_history::jsonb, 'null'::jsonb)), 0) * 30.0),
                    100.0
                )
            WHEN d.domain = 'INNOVATION' THEN
                LEAST(
                    (COALESCE(jsonb_array_length(NULLIF(s.hackathons::jsonb, 'null'::jsonb)), 0) * 40.0) +
                    (COALESCE(jsonb_array_length(NULLIF(s.projects::jsonb, 'null'::jsonb)), 0) * 15.0),
                    100.0
                )
            WHEN d.domain = 'COMMUNICATION' THEN
                LEAST(
                    (COALESCE(jsonb_array_length(NULLIF(s.internship_history::jsonb, 'null'::jsonb)), 0) * 35.0),
                    100.0
                )
            WHEN d.domain = 'DESIGN' THEN
                LEAST(
                    (COALESCE(jsonb_array_length(NULLIF(s.projects::jsonb, 'null'::jsonb)), 0) * 30.0),
                    100.0
                )
            ELSE 0.0
        END AS achievement_component,
        
        -- Certification component per domain (0 - 100)
        CASE 
            WHEN d.domain IN ('TECHNICAL', 'RESEARCH') THEN
                LEAST(COALESCE(jsonb_array_length(NULLIF(s.certifications::jsonb, 'null'::jsonb)), 0) * 33.33, 100.0)
            ELSE
                LEAST(COALESCE(jsonb_array_length(NULLIF(s.certifications::jsonb, 'null'::jsonb)), 0) * 20.0, 100.0)
        END AS certification_component,
        
        -- Resume component per domain (0 - 100)
        LEAST(COALESCE(r.resume_score, 0.0), 100.0) AS resume_component
    FROM public.students s
    CROSS JOIN (VALUES ('TECHNICAL'), ('RESEARCH'), ('INNOVATION'), ('COMMUNICATION'), ('DESIGN')) AS d(domain)
    LEFT JOIN resume_agg r ON s.id = r.student_id AND r.domain = d.domain
),

-- 6. Weighted Domain Score (45/35/10/10 Frozen Formula)
weighted_domain_scores AS (
    SELECT 
        student_id,
        branch,
        cgpa,
        domain,
        ROUND(
            (0.45 * academic_component) + 
            (0.35 * achievement_component) + 
            (0.10 * certification_component) + 
            (0.10 * resume_component), 
        2) AS domain_score
    FROM domain_components
),

-- 7. Relative Cohort Medians & Percentiles
relative_stats AS (
    SELECT 
        branch,
        domain,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY domain_score) AS median_domain_score
    FROM weighted_domain_scores
    GROUP BY branch, domain
),

student_cgpa_percentiles AS (
    SELECT DISTINCT
        id AS student_id,
        branch,
        cgpa,
        PERCENT_RANK() OVER (PARTITION BY branch ORDER BY cgpa) AS cgpa_percentile
    FROM public.students
),

student_domain_percentiles AS (
    SELECT 
        w.student_id,
        w.branch,
        w.domain,
        w.domain_score,
        scp.cgpa,
        scp.cgpa_percentile,
        rs.median_domain_score,
        sa.has_sufficient_history,
        PERCENT_RANK() OVER (PARTITION BY w.branch, w.domain ORDER BY w.domain_score) AS domain_percentile
    FROM weighted_domain_scores w
    JOIN student_cgpa_percentiles scp ON w.student_id = scp.student_id
    JOIN relative_stats rs ON w.branch = rs.branch AND w.domain = rs.domain
    JOIN sem_analysis sa ON w.student_id = sa.student_id
),

-- 8. Hidden Talent Trigger per Domain
hidden_talent_checks AS (
    SELECT 
        dp.student_id,
        dp.domain,
        dp.domain_score,
        dp.domain_percentile,
        CASE 
            WHEN dp.has_sufficient_history = TRUE 
             AND dp.domain_score > dp.median_domain_score + 10.0 
             AND dp.domain_percentile > dp.cgpa_percentile 
            THEN TRUE 
            ELSE FALSE 
        END AS is_domain_hidden_talent
    FROM student_domain_percentiles dp
),

-- 9. Pivoted Student Multidimensional Profile (Single Row per Student)
pivoted_scores AS (
    SELECT 
        dp.student_id,
        MAX(dp.branch) AS branch,
        MAX(dp.cgpa) AS cgpa,
        MAX(dp.cgpa_percentile) AS cgpa_percentile,
        
        MAX(CASE WHEN dp.domain = 'TECHNICAL' THEN dp.domain_score END) AS technical_score,
        MAX(CASE WHEN dp.domain = 'RESEARCH' THEN dp.domain_score END) AS research_score,
        MAX(CASE WHEN dp.domain = 'INNOVATION' THEN dp.domain_score END) AS innovation_score,
        MAX(CASE WHEN dp.domain = 'COMMUNICATION' THEN dp.domain_score END) AS communication_score,
        MAX(CASE WHEN dp.domain = 'DESIGN' THEN dp.domain_score END) AS design_score,
        
        MAX(CASE WHEN dp.domain = 'TECHNICAL' THEN dp.domain_percentile END) AS technical_percentile,
        MAX(CASE WHEN dp.domain = 'RESEARCH' THEN dp.domain_percentile END) AS research_percentile,
        MAX(CASE WHEN dp.domain = 'INNOVATION' THEN dp.domain_percentile END) AS innovation_percentile,
        MAX(CASE WHEN dp.domain = 'COMMUNICATION' THEN dp.domain_percentile END) AS communication_percentile,
        MAX(CASE WHEN dp.domain = 'DESIGN' THEN dp.domain_percentile END) AS design_percentile,
        
        BOOL_OR(htc.is_domain_hidden_talent) AS hidden_talent,
        COALESCE(
            ARRAY_REMOVE(ARRAY_AGG(CASE WHEN htc.is_domain_hidden_talent THEN htc.domain END), NULL),
            ARRAY[]::text[]
        ) AS hidden_talent_domains
    FROM student_domain_percentiles dp
    JOIN hidden_talent_checks htc ON dp.student_id = htc.student_id AND dp.domain = htc.domain
    GROUP BY dp.student_id
)

-- 10. Final Assembly
SELECT 
    p.student_id,
    p.branch,
    p.cgpa,
    p.cgpa_percentile,
    
    p.technical_score,
    p.research_score,
    p.innovation_score,
    p.communication_score,
    p.design_score,
    
    p.technical_percentile,
    p.research_percentile,
    p.innovation_percentile,
    p.communication_percentile,
    p.design_percentile,
    
    ROUND(gp.raw_growth, 2) AS growth_value,
    gp.growth_percentile,
    CASE 
        WHEN NOT gp.has_sufficient_history THEN 'INSUFFICIENT_DATA'
        WHEN gp.growth_percentile >= 0.80 THEN 'HIGH'
        WHEN gp.growth_percentile >= 0.40 THEN 'MODERATE'
        ELSE 'LOW'
    END AS growth_bucket,
    
    CASE 
        WHEN gp.has_sufficient_history AND gp.growth_percentile >= 0.80 THEN TRUE 
        ELSE FALSE 
    END AS high_growth,
    
    p.hidden_talent,
    p.hidden_talent_domains,
    
    sec.academic_evidence_count,
    sec.achievement_evidence_count,
    sec.certification_evidence_count,
    sec.resume_verified_count,
    sec.resume_pending_count,
    
    gp.has_sufficient_history
FROM pivoted_scores p
JOIN growth_percentiles gp ON p.student_id = gp.student_id
JOIN student_evidence_counts sec ON p.student_id = sec.student_id;


-- ============================================================
-- 2. DETERMINISTIC OPPORTUNITY ELIGIBILITY & FIT (PHASE 3)
-- Evaluates hard eligibility rules and computes fit scores.
-- ============================================================
CREATE OR REPLACE VIEW outcomes.v_opportunity_eligibility_and_fit AS
WITH 
-- 1. Project Active Capacity
project_capacity AS (
    SELECT 
        p.project_id,
        p.faculty_id,
        p.title AS project_title,
        p.capacity,
        COUNT(pm.membership_id) FILTER (WHERE pm.status = 'ACTIVE') AS current_members,
        (p.capacity > COUNT(pm.membership_id) FILTER (WHERE pm.status = 'ACTIVE')) AS capacity_available
    FROM research.project p
    LEFT JOIN research.project_member pm ON p.project_id = pm.project_id
    WHERE p.status = 'ACTIVE'
    GROUP BY p.project_id, p.faculty_id, p.title, p.capacity
),

-- 2. Requirement Evaluations per Student & Project Requirement
req_eval AS (
    SELECT 
        s.student_id,
        s.branch,
        p.project_id,
        p.project_title,
        p.capacity_available,
        pr.requirement_id,
        pr.domain,
        pr.skill,
        pr.min_score,
        pr.is_required,
        pr.weight,
        
        -- Domain Requirement Check
        CASE WHEN pr.domain IS NOT NULL THEN
            CASE 
                WHEN pr.domain = 'TECHNICAL' THEN (s.technical_score >= pr.min_score)
                WHEN pr.domain = 'RESEARCH' THEN (s.research_score >= pr.min_score)
                WHEN pr.domain = 'INNOVATION' THEN (s.innovation_score >= pr.min_score)
                WHEN pr.domain = 'COMMUNICATION' THEN (s.communication_score >= pr.min_score)
                WHEN pr.domain = 'DESIGN' THEN (s.design_score >= pr.min_score)
                ELSE TRUE
            END
        ELSE TRUE END AS domain_req_passed,
        
        -- Skill Requirement Check (match in student skills JSON array)
        CASE WHEN pr.skill IS NOT NULL THEN
            EXISTS (
                SELECT 1 
                FROM jsonb_array_elements(NULLIF(st.skills::jsonb, 'null'::jsonb)) AS sk
                WHERE LOWER(sk->>'skill') = LOWER(pr.skill)
            )
        ELSE TRUE END AS skill_req_passed,
        
        -- Domain score value for alignment
        CASE 
            WHEN pr.domain = 'TECHNICAL' THEN s.technical_score
            WHEN pr.domain = 'RESEARCH' THEN s.research_score
            WHEN pr.domain = 'INNOVATION' THEN s.innovation_score
            WHEN pr.domain = 'COMMUNICATION' THEN s.communication_score
            WHEN pr.domain = 'DESIGN' THEN s.design_score
            ELSE s.research_score
        END AS domain_score_val,
        
        s.high_growth,
        COALESCE(s.growth_percentile, 0.5) AS growth_percentile
        
    FROM outcomes.v_student_strength_profile s
    JOIN public.students st ON s.student_id = st.id
    CROSS JOIN project_capacity p
    LEFT JOIN research.project_requirement pr ON p.project_id = pr.project_id
),

-- 3. Hard Eligibility & Requirement Aggregation
eligibility_summary AS (
    SELECT 
        student_id,
        project_id,
        project_title,
        capacity_available,
        
        -- Hard Eligibility: Passes ALL required requirements (both domain & skill)
        BOOL_AND(
            CASE 
                WHEN is_required = TRUE THEN (domain_req_passed AND skill_req_passed)
                ELSE TRUE 
            END
        ) AS eligible,
        
        -- Aggregated Failed Required Requirements as JSON/Array
        COALESCE(
            ARRAY_REMOVE(
                ARRAY_AGG(
                    CASE 
                        WHEN is_required = TRUE AND NOT (domain_req_passed AND skill_req_passed) THEN
                            COALESCE(domain, '') || CASE WHEN skill IS NOT NULL THEN ' ' || skill ELSE '' END || ' (Min: ' || min_score || ')'
                    END
                ), NULL
            ), ARRAY[]::text[]
        ) AS failed_required_requirements,

        -- Aggregated Matched Skills
        COALESCE(
            ARRAY_REMOVE(
                ARRAY_AGG(
                    CASE WHEN skill IS NOT NULL AND skill_req_passed THEN skill END
                ), NULL
            ), ARRAY[]::text[]
        ) AS matched_skills,

        -- Aggregated Missing Preferred Skills
        COALESCE(
            ARRAY_REMOVE(
                ARRAY_AGG(
                    CASE WHEN skill IS NOT NULL AND is_required = FALSE AND NOT skill_req_passed THEN skill END
                ), NULL
            ), ARRAY[]::text[]
        ) AS missing_preferred_skills,

        -- Domain Alignment Score (0 - 100)
        ROUND(AVG(COALESCE(domain_score_val, 70.0)), 2) AS domain_alignment,
        
        -- Skill Alignment Score (0 - 100)
        ROUND(
            (COUNT(CASE WHEN skill IS NOT NULL AND skill_req_passed THEN 1 END)::numeric / 
             NULLIF(COUNT(CASE WHEN skill IS NOT NULL THEN 1 END), 0)::numeric) * 100.0, 
        2) AS raw_skill_alignment
        
    FROM req_eval
    GROUP BY student_id, project_id, project_title, capacity_available
),

-- 4. Interest Alignment Calculation
interest_summary AS (
    SELECT 
        e.student_id,
        e.project_id,
        CASE 
            WHEN EXISTS (SELECT 1 FROM studentlife.student_interest si WHERE si.student_id = e.student_id) THEN
                CASE WHEN EXISTS (
                    SELECT 1 FROM studentlife.student_interest si 
                    WHERE si.student_id = e.student_id 
                      AND (LOWER(e.project_title) LIKE '%' || LOWER(si.area) || '%' 
                           OR LOWER(si.area) LIKE '%' || LOWER(e.project_title) || '%')
                ) THEN 100.0 ELSE 50.0 END
            ELSE 50.0 -- Neutral baseline when no interest is declared
        END AS interest_match
    FROM eligibility_summary e
),

-- 5. Deterministic Fit Score Assembly (0 - 100)
fit_assembly AS (
    SELECT 
        es.student_id,
        es.project_id,
        es.project_title,
        es.capacity_available,
        COALESCE(es.eligible, TRUE) AS eligible,
        es.failed_required_requirements,
        es.matched_skills,
        es.missing_preferred_skills,
        
        es.domain_alignment,
        COALESCE(es.raw_skill_alignment, 100.0) AS skill_alignment,
        ins.interest_match,
        
        ROUND(COALESCE(s.growth_percentile::numeric, 0.5) * 100.0, 2) AS growth_component,
        ROUND((0.60 * es.domain_alignment) + (0.40 * COALESCE(es.raw_skill_alignment, 100.0)), 2) AS requirement_alignment,

        -- Authoritative Fit Formula (0 - 100):
        -- 0.40 * domain_alignment + 0.30 * skill_alignment + 0.15 * interest_match + 0.15 * growth_component
        ROUND(
            (0.40 * es.domain_alignment) + 
            (0.30 * COALESCE(es.raw_skill_alignment, 100.0)) + 
            (0.15 * ins.interest_match) + 
            (0.15 * (COALESCE(s.growth_percentile::numeric, 0.5) * 100.0)),
        2) AS fit_score

    FROM eligibility_summary es
    JOIN outcomes.v_student_strength_profile s ON es.student_id = s.student_id
    JOIN interest_summary ins ON es.student_id = ins.student_id AND es.project_id = ins.project_id
)

SELECT 
    f.student_id,
    f.project_id,
    f.project_title,
    f.capacity_available,
    f.eligible,
    f.fit_score,
    f.domain_alignment,
    f.skill_alignment,
    f.interest_match,
    f.growth_component,
    f.requirement_alignment,
    f.failed_required_requirements,
    f.matched_skills,
    f.missing_preferred_skills,
    ROW_NUMBER() OVER (
        PARTITION BY f.student_id 
        ORDER BY f.eligible DESC, f.fit_score DESC, f.project_id ASC
    ) AS fit_rank
FROM fit_assembly f;


-- ============================================================
-- 3. DETERMINISTIC FACULTY MENTOR COMPATIBILITY (PHASE 3)
-- Maps student domain strength, skills, and interests against faculty expertise & capacity.
-- ============================================================
CREATE OR REPLACE VIEW outcomes.v_faculty_mentor_compatibility AS
WITH faculty_active_projects AS (
    SELECT 
        f.faculty_id,
        f.name AS faculty_name,
        f.department,
        f.research_areas,
        p.project_id,
        p.title AS project_title,
        p.capacity,
        COUNT(pm.membership_id) FILTER (WHERE pm.status = 'ACTIVE') AS current_members,
        (p.capacity > COUNT(pm.membership_id) FILTER (WHERE pm.status = 'ACTIVE')) AS capacity_available
    FROM people.faculty_expertise f
    JOIN research.project p ON f.faculty_id = p.faculty_id AND p.status = 'ACTIVE'
    LEFT JOIN research.project_member pm ON p.project_id = pm.project_id
    GROUP BY f.faculty_id, f.name, f.department, f.research_areas, p.project_id, p.title, p.capacity
),
faculty_matches AS (
    SELECT 
        s.student_id,
        f.faculty_id,
        f.faculty_name,
        f.department AS faculty_department,
        f.project_id,
        f.project_title,
        f.capacity_available,
        
        -- Research Area Overlap Score (0 - 100)
        CASE 
            WHEN EXISTS (
                SELECT 1 
                FROM unnest(f.research_areas) AS ra
                JOIN studentlife.student_interest si ON si.student_id = s.student_id
                WHERE LOWER(ra) LIKE '%' || LOWER(si.area) || '%' OR LOWER(si.area) LIKE '%' || LOWER(ra) || '%'
            ) THEN 100.0
            ELSE 20.0
        END AS research_overlap_score,

        s.research_score AS domain_strength_score,
        
        -- Overall Faculty Compatibility Score (0 - 100)
        ROUND(
            (0.50 * CASE 
                WHEN EXISTS (
                    SELECT 1 
                    FROM unnest(f.research_areas) AS ra
                    JOIN studentlife.student_interest si ON si.student_id = s.student_id
                    WHERE LOWER(ra) LIKE '%' || LOWER(si.area) || '%' OR LOWER(si.area) LIKE '%' || LOWER(ra) || '%'
                ) THEN 100.0
                ELSE 20.0
            END) +
            (0.30 * s.research_score) +
            (0.20 * COALESCE(s.growth_percentile::numeric * 100.0, 50.0)),
        2) AS compatibility_score

    FROM outcomes.v_student_strength_profile s
    CROSS JOIN faculty_active_projects f
)
SELECT 
    fm.student_id,
    fm.faculty_id,
    fm.faculty_name,
    fm.faculty_department,
    fm.project_id,
    fm.project_title,
    fm.capacity_available,
    fm.compatibility_score,
    CASE WHEN fm.compatibility_score >= 60.0 THEN TRUE ELSE FALSE END AS is_strong_match
FROM faculty_matches fm
WHERE fm.compatibility_score >= 60.0;
