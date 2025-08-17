-- First, insert the photo data (family_id can be NULL)
INSERT INTO
    photos (
        id,
        name,
        url,
        year,
        season,
        description,
        family_id,
        uploaded_at
    )
VALUES (
        '1f9982d0-5d3a-4b33-9d20-de63fe48efa2',
        'images.jpeg',
        'https://mementoboxstorage.blob.core.windows.net/photo/1f9982d0-5d3a-4b33-9d20-de63fe48efa2_images.jpeg.jpg',
        2024,
        'spring',
        'Sample photo description',
        NULL, -- family_id is nullable
        NOW()
    );

-- Then, insert the conversation data
INSERT INTO
    conversations (id, photo_id, created_at)
VALUES (
        '22222222-2222-2222-2222-222222222222',
        '11111111-1111-1111-1111-111111111111',
        NOW()
    );