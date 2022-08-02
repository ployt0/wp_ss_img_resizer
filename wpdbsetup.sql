CREATE DATABASE IF NOT EXISTS wordpress;
CREATE USER IF NOT EXISTS wordpressuser232@'localhost' IDENTIFIED BY 'galoshes';
GRANT SELECT,INSERT,UPDATE,DELETE,CREATE,DROP,ALTER ON wordpress.* TO wordpressuser232@'localhost';
FLUSH PRIVILEGES;
-- SHOW global VARIABLES like 'max_allowed_packet';
-- SET global max_allowed_packet=67108864;
