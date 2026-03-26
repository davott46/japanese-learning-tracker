-- =========================
-- RESET
-- =========================
--TRUNCATE study_logs CASCADE; make sure not to TRUNCATE study_logs!
TRUNCATE day_tasks CASCADE;
TRUNCATE days CASCADE;
TRUNCATE lessons CASCADE;
TRUNCATE task_templates CASCADE;

-- =========================
-- CONSTRAINTS
-- =========================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'lessons_code_unique'
    ) THEN
        ALTER TABLE lessons ADD CONSTRAINT lessons_code_unique UNIQUE (code);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'days_day_number_unique'
    ) THEN
        ALTER TABLE days ADD CONSTRAINT days_day_number_unique UNIQUE (day_number);
    END IF;
END $$;

-- =========================
-- LESSONS
-- =========================
INSERT INTO lessons (code, name, book, goal) VALUES
('L7','Genki I L7','Genki I','Past tense + casual forms'),
('L8','Genki I L8','Genki I','Short forms + informal speech'),
('L9','Genki I L9','Genki I','Past short forms + quoting'),
('L10','Genki I L10','Genki I','Comparison + degree'),
('L11','Genki I L11','Genki I','〜たい + counting'),
('L12','Genki I L12','Genki I','〜んです explanation'),
('L13','Genki II L13','Genki II','Potential form'),
('L14','Genki II L14','Genki II','Volitional form'),
('L15','Genki II L15','Genki II','Transitive/intransitive verbs'),
('L16','Genki II L16','Genki II','Giving/receiving verbs'),
('L17','Genki II L17','Genki II','〜そう + hearsay'),
('L18','Genki II L18','Genki II','Causative intro'),
('L19','Genki II L19','Genki II','Honorific verbs'),
('L20','Genki II L20','Genki II','Extra-modest expressions'),
('L21','Genki II L21','Genki II','Passive form'),
('L22','Genki II L22','Genki II','Causative form'),
('L23','Genki II L23','Genki II','Causative-passive');

-- =========================
-- TASK TEMPLATES
-- =========================
INSERT INTO task_templates (block, name, duration) VALUES
('Review','Anki Review',1.0),
('Review','Review last 2 lessons',0.5),
('Lesson','Dialogue listening + shadowing',0.5),
('Lesson','Vocabulary + Anki',0.75),
('Lesson','Grammar study + sentences',1.25),
('Practice','Workbook exercises',1.0),
('Practice','Speak answers aloud',0.5),
('Immersion','Listening practice',0.5);

-- =========================
-- DAYS
-- =========================
INSERT INTO days (day_number, week, lesson_id, type)
SELECT
    d.day_number,
    d.week,
    l.id,
    d.type
FROM (
    VALUES
    (1,1,'L7','lesson'),
    (2,1,'L8','lesson'),
    (3,1,'L9','lesson'),
    (4,1,'L10','lesson'),
    (5,1,'L11','lesson'),
    (6,1,'L12','lesson'),
    (7,1,NULL,'review'),

    (8,2,NULL,'review'),
    (9,2,NULL,'review'),
    (10,2,NULL,'review'),
    (11,2,NULL,'review'),
    (12,2,NULL,'review'),
    (13,2,NULL,'weak_points'),
    (14,2,NULL,'light'),

    (15,3,'L13','lesson'),
    (16,3,'L14','lesson'),
    (17,3,'L15','lesson'),
    (18,3,'L16','lesson'),
    (19,3,NULL,'review'),
    (20,3,NULL,'weak_points'),
    (21,3,NULL,'light'),

    (22,4,'L17','lesson'),
    (23,4,'L18','lesson'),
    (24,4,'L19','lesson'),
    (25,4,NULL,'review'),
    (26,4,NULL,'weak_points'),
    (27,4,NULL,'speaking'),
    (28,4,NULL,'light'),

    (29,5,'L20','lesson'),
    (30,5,'L21','lesson'),
    (31,5,'L22','lesson'),
    (32,5,'L23','lesson'),
    (33,5,NULL,'review'),
    (34,5,NULL,'weak_points'),
    (35,5,NULL,'light'),

    (36,6,NULL,'grammar_review_1'),
    (37,6,NULL,'grammar_review_2'),
    (38,6,NULL,'workbook_review'),
    (39,6,NULL,'speaking'),
    (40,6,NULL,'listening'),
    (41,6,NULL,'weak_points'),
    (42,6,NULL,'final_review')

) AS d(day_number, week, lesson_code, type)
LEFT JOIN lessons l ON l.code = d.lesson_code;

-- =========================
-- DAY TASKS GENERATION
-- =========================
INSERT INTO day_tasks (day_id, task_template_id, completed, position)
SELECT
    d.id,
    tt.id,
    FALSE,
    ROW_NUMBER() OVER (PARTITION BY d.id ORDER BY tt.id)
FROM days d
JOIN task_templates tt ON (
    -- lesson days
    (d.type = 'lesson' AND tt.name IN (
        'Dialogue listening + shadowing',
        'Vocabulary + Anki',
        'Grammar study + sentences',
        'Workbook exercises',
        'Speak answers aloud'
    ))

    OR

    -- review / weak / grammar / final
    (d.type IN ('review','weak_points','grammar_review_1','grammar_review_2','final_review')
     AND tt.name IN ('Anki Review','Review last 2 lessons'))

    OR

    -- speaking days
    (d.type = 'speaking'
     AND tt.name IN ('Speak answers aloud','Listening practice'))

    OR

    -- listening days
    (d.type = 'listening'
     AND tt.name = 'Listening practice')

    OR

    -- light days
    (d.type = 'light'
     AND tt.name = 'Anki Review')
);