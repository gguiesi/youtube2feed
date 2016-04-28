BEGIN TRANSACTION;
CREATE TABLE "episode" (
                    `id`    INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
                    `title` TEXT NOT NULL,
                    `pub_date`  TEXT NOT NULL,
                    `webpage_url` TEXT NOT NULL UNIQUE,
                    `url`   TEXT NOT NULL UNIQUE,
                    `channel_id`    INTEGER NOT NULL,
                    `flg_feed`  NUMERIC NOT NULL DEFAULT 0,
                    `last_update` TEXT NOT NULL,
                    FOREIGN KEY(`channel_id`) REFERENCES `channel`(`id`) ON DELETE CASCADE
                );
CREATE TABLE "channel" (
                    `id`    INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
                    `name`  TEXT NOT NULL UNIQUE,
                    `url`   TEXT NOT NULL UNIQUE,
                    `image_url` TEXT NOT NULL,
                    `last_update` TEXT NOT NULL
                );
COMMIT;
