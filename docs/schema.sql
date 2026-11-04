-- MySQL 8 schema for HomeServe. The app also runs on SQLite through SQLAlchemy.
CREATE DATABASE IF NOT EXISTS homeserve CHARACTER SET utf8mb4;
USE homeserve;

CREATE TABLE users (
  id INT PRIMARY KEY AUTO_INCREMENT,
  full_name VARCHAR(120) NOT NULL,
  email VARCHAR(180) NOT NULL UNIQUE,
  phone VARCHAR(20) DEFAULT '',
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(20) NOT NULL,
  status VARCHAR(20) DEFAULT 'active',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE customers (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NOT NULL UNIQUE,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE subscription_plans (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(80) NOT NULL,
  price DOUBLE DEFAULT 0,
  commission_rate DOUBLE DEFAULT 15,
  description TEXT,
  features TEXT,
  is_active TINYINT(1) DEFAULT 1
);

CREATE TABLE service_providers (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NOT NULL UNIQUE,
  business_name VARCHAR(160) NOT NULL,
  bio TEXT,
  experience_years INT DEFAULT 1,
  verification_status VARCHAR(20) DEFAULT 'pending',
  document_url VARCHAR(500) DEFAULT '',
  rejection_reason VARCHAR(300) DEFAULT '',
  commission_rate DOUBLE DEFAULT 15,
  rating_avg DOUBLE DEFAULT 0,
  rating_count INT DEFAULT 0,
  plan_id INT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (plan_id) REFERENCES subscription_plans(id)
);

CREATE TABLE technicians (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NOT NULL UNIQUE,
  provider_id INT NOT NULL,
  skills VARCHAR(300) DEFAULT '',
  status VARCHAR(20) DEFAULT 'active',
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (provider_id) REFERENCES service_providers(id)
);

CREATE TABLE addresses (
  id INT PRIMARY KEY AUTO_INCREMENT,
  customer_id INT NOT NULL,
  label VARCHAR(40) DEFAULT 'Home',
  line1 VARCHAR(200) NOT NULL,
  city VARCHAR(80) NOT NULL,
  state VARCHAR(80) DEFAULT 'Gujarat',
  pincode VARCHAR(10) DEFAULT '',
  is_default TINYINT(1) DEFAULT 0,
  FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE service_categories (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  slug VARCHAR(100) NOT NULL UNIQUE,
  description TEXT,
  icon VARCHAR(40) DEFAULT 'bolt',
  parent_id INT NULL,
  is_active TINYINT(1) DEFAULT 1,
  FOREIGN KEY (parent_id) REFERENCES service_categories(id)
);

CREATE TABLE services (
  id INT PRIMARY KEY AUTO_INCREMENT,
  category_id INT NOT NULL,
  name VARCHAR(140) NOT NULL,
  description TEXT,
  base_price DOUBLE DEFAULT 0,
  duration_mins INT DEFAULT 60,
  image_url VARCHAR(500) DEFAULT '',
  status VARCHAR(20) DEFAULT 'active',
  FOREIGN KEY (category_id) REFERENCES service_categories(id)
);

CREATE TABLE provider_services (
  id INT PRIMARY KEY AUTO_INCREMENT,
  provider_id INT NOT NULL,
  service_id INT NOT NULL,
  price DOUBLE NOT NULL,
  description TEXT,
  status VARCHAR(20) DEFAULT 'active',
  FOREIGN KEY (provider_id) REFERENCES service_providers(id),
  FOREIGN KEY (service_id) REFERENCES services(id)
);

CREATE TABLE service_areas (
  id INT PRIMARY KEY AUTO_INCREMENT,
  provider_id INT NOT NULL,
  city VARCHAR(80) NOT NULL,
  pincode VARCHAR(10) DEFAULT '',
  FOREIGN KEY (provider_id) REFERENCES service_providers(id)
);

CREATE TABLE availability_slots (
  id INT PRIMARY KEY AUTO_INCREMENT,
  provider_id INT NOT NULL,
  day_of_week INT NOT NULL,
  start_time VARCHAR(5) NOT NULL,
  end_time VARCHAR(5) NOT NULL,
  is_active TINYINT(1) DEFAULT 1,
  FOREIGN KEY (provider_id) REFERENCES service_providers(id)
);

CREATE TABLE bookings (
  id INT PRIMARY KEY AUTO_INCREMENT,
  booking_code VARCHAR(20) NOT NULL UNIQUE,
  customer_id INT NOT NULL,
  provider_id INT NOT NULL,
  service_id INT NOT NULL,
  provider_service_id INT NOT NULL,
  technician_id INT NULL,
  address_text VARCHAR(300) DEFAULT '',
  city VARCHAR(80) DEFAULT '',
  scheduled_date VARCHAR(10) NOT NULL,
  scheduled_time VARCHAR(5) NOT NULL,
  status VARCHAR(30) DEFAULT 'Pending',
  payment_status VARCHAR(20) DEFAULT 'Pending',
  problem_note TEXT,
  remarks TEXT,
  cancel_reason VARCHAR(300) DEFAULT '',
  subtotal DOUBLE DEFAULT 0,
  discount DOUBLE DEFAULT 0,
  taxable DOUBLE DEFAULT 0,
  gst DOUBLE DEFAULT 0,
  commission DOUBLE DEFAULT 0,
  provider_earning DOUBLE DEFAULT 0,
  total DOUBLE DEFAULT 0,
  coupon_code VARCHAR(40) DEFAULT '',
  slot_key VARCHAR(80) NULL UNIQUE,
  arrived_at DATETIME NULL,
  completed_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (customer_id) REFERENCES customers(id),
  FOREIGN KEY (provider_id) REFERENCES service_providers(id),
  FOREIGN KEY (service_id) REFERENCES services(id),
  FOREIGN KEY (provider_service_id) REFERENCES provider_services(id),
  FOREIGN KEY (technician_id) REFERENCES technicians(id)
);

CREATE TABLE booking_assignments (
  id INT PRIMARY KEY AUTO_INCREMENT,
  booking_id INT NOT NULL,
  technician_id INT NOT NULL,
  status VARCHAR(20) DEFAULT 'assigned',
  remarks TEXT,
  arrived_at DATETIME NULL,
  completed_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (booking_id) REFERENCES bookings(id),
  FOREIGN KEY (technician_id) REFERENCES technicians(id)
);

CREATE TABLE booking_images (
  id INT PRIMARY KEY AUTO_INCREMENT,
  booking_id INT NOT NULL,
  url VARCHAR(500) NOT NULL,
  kind VARCHAR(20) DEFAULT 'problem',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (booking_id) REFERENCES bookings(id)
);

CREATE TABLE payments (
  id INT PRIMARY KEY AUTO_INCREMENT,
  booking_id INT NOT NULL,
  amount DOUBLE NOT NULL,
  commission DOUBLE DEFAULT 0,
  status VARCHAR(20) DEFAULT 'Pending',
  method VARCHAR(40) DEFAULT 'razorpay_test',
  order_id VARCHAR(80) DEFAULT '',
  txn_id VARCHAR(80) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (booking_id) REFERENCES bookings(id)
);

CREATE TABLE invoices (
  id INT PRIMARY KEY AUTO_INCREMENT,
  payment_id INT NOT NULL UNIQUE,
  booking_id INT NOT NULL,
  invoice_number VARCHAR(40) NOT NULL UNIQUE,
  amount DOUBLE NOT NULL,
  issued_on VARCHAR(10) NOT NULL,
  FOREIGN KEY (payment_id) REFERENCES payments(id),
  FOREIGN KEY (booking_id) REFERENCES bookings(id)
);

CREATE TABLE coupons (
  id INT PRIMARY KEY AUTO_INCREMENT,
  code VARCHAR(40) NOT NULL UNIQUE,
  discount_type VARCHAR(20) DEFAULT 'percent',
  value DOUBLE NOT NULL,
  min_amount DOUBLE DEFAULT 0,
  max_discount DOUBLE NULL,
  expires_on VARCHAR(10) DEFAULT '',
  is_active TINYINT(1) DEFAULT 1
);

CREATE TABLE reviews (
  id INT PRIMARY KEY AUTO_INCREMENT,
  booking_id INT NOT NULL UNIQUE,
  customer_id INT NOT NULL,
  provider_id INT NOT NULL,
  rating INT NOT NULL,
  comment TEXT,
  provider_response TEXT,
  is_visible TINYINT(1) DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (booking_id) REFERENCES bookings(id),
  FOREIGN KEY (customer_id) REFERENCES customers(id),
  FOREIGN KEY (provider_id) REFERENCES service_providers(id)
);

CREATE TABLE complaints (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NOT NULL,
  booking_id INT NULL,
  subject VARCHAR(160) NOT NULL,
  description TEXT,
  status VARCHAR(20) DEFAULT 'Open',
  admin_note TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (booking_id) REFERENCES bookings(id)
);

CREATE TABLE notifications (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NOT NULL,
  title VARCHAR(160) NOT NULL,
  body TEXT,
  ntype VARCHAR(40) DEFAULT 'info',
  is_read TINYINT(1) DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE provider_earnings (
  id INT PRIMARY KEY AUTO_INCREMENT,
  provider_id INT NOT NULL,
  booking_id INT NOT NULL,
  payment_id INT NULL,
  gross DOUBLE DEFAULT 0,
  commission DOUBLE DEFAULT 0,
  net DOUBLE DEFAULT 0,
  status VARCHAR(20) DEFAULT 'accrued',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (provider_id) REFERENCES service_providers(id),
  FOREIGN KEY (booking_id) REFERENCES bookings(id),
  FOREIGN KEY (payment_id) REFERENCES payments(id)
);

CREATE TABLE favorites (
  id INT PRIMARY KEY AUTO_INCREMENT,
  customer_id INT NOT NULL,
  provider_id INT NOT NULL,
  UNIQUE KEY uq_favorite (customer_id, provider_id),
  FOREIGN KEY (customer_id) REFERENCES customers(id),
  FOREIGN KEY (provider_id) REFERENCES service_providers(id)
);

CREATE TABLE password_resets (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NOT NULL,
  code VARCHAR(10) NOT NULL,
  expires_at DATETIME NOT NULL,
  used TINYINT(1) DEFAULT 0,
  FOREIGN KEY (user_id) REFERENCES users(id)
);
