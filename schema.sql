-- init database

drop database if exists awesome;

create database awesome;

use awesome;

--                                                    USER                             PSWD
grant select, insert, update, delete on awesome.* to 'root'@'localhost' identified by 'root';

create table users (
    `id` varchar(50) not null,
    `email` varchar(50) not null,
    `password` varchar(50) not null,
    `admin` bool not null,
    `name` varchar(50) not null,
    `image` varchar(500) not null,
    `created_at` real not null,
    `last_login` real not null,
    unique key `idx_email` (`email`),
    key `idx_created_at` (`created_at`),
    primary key (`id`)
) engine=innodb default charset=utf8;

create table blogs (
    `id` varchar(50) not null,
    `user_id` varchar(50) not null,
    `user_name` varchar(50) not null,
    `user_image` varchar(500) not null,
    `title` varchar(50) not null,
    `summary` varchar(200) not null,
    `content` mediumtext not null,
    `created_at` real not null,
    `latest_reply` real not null,
    key `idx_created_at` (`created_at`),
    primary key (`id`)
) engine=innodb default charset=utf8;

create table comments (
    `id` varchar(50) not null,
    `blog_id` varchar(50) not null,
    `blog_title` varchar(50) not null,
    `user_id` varchar(50) not null,
    `user_name` varchar(50) not null,
    `user_image` varchar(500) not null,
    `content` mediumtext not null,
    `created_at` real not null,
    key `idx_created_at` (`created_at`),
    primary key (`id`)
) engine=innodb default charset=utf8;

-- email / password:
-- zlfeng_2012@163.com / admin

insert into users (`id`, `email`, `password`, `admin`, `name`, `image`, `created_at`, `last_login`) values ('10000', 'zlfeng_2012@163.com', '21232f297a57a5a743894a0e4a801fc3', 1, 'Administrator', 'http://www.gravatar.com/avatar/ea1c6edeb3ef3bc5cb046addf54adf2c?d=mm&s=120', 1402909113.628, 1402909113);
