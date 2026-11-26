-- CampusConnect Database Schema for MySQL 8.0+
-- College Event, Club & Expense Management Portal

CREATE DATABASE IF NOT EXISTS `campus_connect` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `campus_connect`;

-- 1. Users Table
CREATE TABLE IF NOT EXISTS `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(100) NOT NULL,
    `email` VARCHAR(120) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `role` ENUM('admin', 'coordinator', 'student') NOT NULL DEFAULT 'student',
    `is_active` BOOLEAN DEFAULT TRUE,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_users_role` (`role`),
    INDEX `idx_users_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Clubs Table
CREATE TABLE IF NOT EXISTS `clubs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(100) NOT NULL UNIQUE,
    `description` TEXT,
    `category` VARCHAR(50) NOT NULL DEFAULT 'General',
    `contact_info` VARCHAR(150) DEFAULT NULL,
    `coordinator_id` INT NULL,
    `logo_url` VARCHAR(255) DEFAULT NULL,
    `status` ENUM('pending', 'approved', 'rejected') NOT NULL DEFAULT 'approved',
    `is_archived` BOOLEAN NOT NULL DEFAULT FALSE,
    `allocated_budget` DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_clubs_coordinator` FOREIGN KEY (`coordinator_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2b. Club Memberships Table
CREATE TABLE IF NOT EXISTS `club_memberships` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `club_id` INT NOT NULL,
    `user_id` INT NOT NULL,
    `member_role` VARCHAR(50) NOT NULL DEFAULT 'Member',
    `joined_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_memberships_club` FOREIGN KEY (`club_id`) REFERENCES `clubs` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_memberships_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `uq_club_member` UNIQUE (`club_id`, `user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Events Table
CREATE TABLE IF NOT EXISTS `events` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `club_id` INT NOT NULL,
    `title` VARCHAR(150) NOT NULL,
    `description` TEXT,
    `venue` VARCHAR(150) NOT NULL,
    `category` VARCHAR(50) NOT NULL DEFAULT 'General',
    `event_date` DATETIME NOT NULL,
    `reg_deadline` DATETIME NOT NULL,
    `capacity` INT NOT NULL DEFAULT 100,
    `banner_image` VARCHAR(255) DEFAULT NULL,
    `allocated_budget` DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    `status` ENUM('draft', 'published', 'completed', 'cancelled') NOT NULL DEFAULT 'draft',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_events_club` FOREIGN KEY (`club_id`) REFERENCES `clubs` (`id`) ON DELETE CASCADE,
    INDEX `idx_events_status` (`status`),
    INDEX `idx_events_date` (`event_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Registrations Table
CREATE TABLE IF NOT EXISTS `registrations` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `event_id` INT NOT NULL,
    `user_id` INT NOT NULL,
    `registered_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `attended` BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT `fk_registrations_event` FOREIGN KEY (`event_id`) REFERENCES `events` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_registrations_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `uq_event_user` UNIQUE (`event_id`, `user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Expenses Table
CREATE TABLE IF NOT EXISTS `expenses` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `event_id` INT NOT NULL,
    `title` VARCHAR(150) NOT NULL,
    `amount` DECIMAL(10, 2) NOT NULL,
    `category` VARCHAR(50) NOT NULL,
    `receipt_file` VARCHAR(255) DEFAULT NULL,
    `status` ENUM('pending', 'approved', 'rejected') NOT NULL DEFAULT 'pending',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_expenses_event` FOREIGN KEY (`event_id`) REFERENCES `events` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Certificates Table
CREATE TABLE IF NOT EXISTS `certificates` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `event_id` INT NOT NULL,
    `user_id` INT NOT NULL,
    `certificate_uid` VARCHAR(64) NOT NULL UNIQUE,
    `issued_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `download_count` INT NOT NULL DEFAULT 0,
    CONSTRAINT `fk_certificates_event` FOREIGN KEY (`event_id`) REFERENCES `events` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_certificates_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. Event Gallery Table
CREATE TABLE IF NOT EXISTS `event_gallery` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `event_id` INT NOT NULL,
    `image_url` VARCHAR(255) NOT NULL,
    `caption` VARCHAR(255) DEFAULT NULL,
    `uploaded_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_gallery_event` FOREIGN KEY (`event_id`) REFERENCES `events` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. Feedback Table
CREATE TABLE IF NOT EXISTS `feedback` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `event_id` INT NOT NULL,
    `user_id` INT NOT NULL,
    `rating` INT NOT NULL CHECK (`rating` BETWEEN 1 AND 5),
    `comments` TEXT DEFAULT NULL,
    `submitted_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_feedback_event` FOREIGN KEY (`event_id`) REFERENCES `events` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_feedback_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `uq_feedback_event_user` UNIQUE (`event_id`, `user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
