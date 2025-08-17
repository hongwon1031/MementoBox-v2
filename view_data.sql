-- 1. 모든 photos 데이터 조회
SELECT * FROM photos;

-- 2. 특정 photo 조회 (방금 삽입한 데이터)
SELECT * FROM photos 
WHERE id = '11111111-1111-1111-1111-111111111111';

-- 3. 모든 conversations 데이터 조회
SELECT * FROM conversations;

-- 4. 특정 conversation 조회 (방금 삽입한 데이터)
SELECT * FROM conversations 
WHERE id = '22222222-2222-2222-2222-222222222222';

-- 5. photo와 conversation을 JOIN해서 함께 조회
SELECT 
    p.id as photo_id,
    p.name as photo_name,
    p.url as photo_url,
    p.year,
    p.season,
    c.id as conversation_id,
    c.created_at as conversation_created_at
FROM photos p
LEFT JOIN conversations c ON p.id = c.photo_id
WHERE p.id = '11111111-1111-1111-1111-111111111111';

-- 6. 최근 삽입된 데이터들 확인 (시간순)
SELECT 'photos' as table_name, id, uploaded_at as created_at FROM photos
UNION ALL
SELECT 'conversations' as table_name, id, created_at FROM conversations
ORDER BY created_at DESC
LIMIT 10; 