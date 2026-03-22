-- ════ https://demo-shop.example.com/ ════

CREATE TABLE "Category" (
    "category" TEXT,
    "items" TEXT,
    "best_seller" TEXT
);


-- ════ https://demo-shop.example.com/products ════

CREATE TABLE "Product" (
    "product_name" TEXT,
    "category" TEXT,
    "price" TEXT,
    "stock" TEXT,
    "rating" TEXT
);

CREATE TABLE "ProductSearch" (
    "query" TEXT,
    "category" TEXT,
    "min_price" INTEGER,
    "max_price" INTEGER,
    "sort_by" TEXT
);


-- ════ https://demo-shop.example.com/products/1 ════

CREATE TABLE "ProductSpecification" (
    "specification" TEXT,
    "value" TEXT
);

CREATE TABLE "Review" (
    "reviewer" TEXT,
    "rating" TEXT,
    "date" TEXT,
    "comment" TEXT
);

CREATE TABLE "CartItem" (
    "product_id" INTEGER,
    "quantity" INTEGER,
    "color" TEXT
);


-- ════ https://demo-shop.example.com/cart ════

CREATE TABLE "Cart" (
    "product" TEXT,
    "price" TEXT,
    "quantity" TEXT,
    "subtotal" TEXT
);

CREATE TABLE "Checkout" (
    "shipping_name" TEXT,
    "shipping_email" VARCHAR,
    "shipping_address" TEXT,
    "shipping_city" TEXT,
    "shipping_zip" TEXT,
    "payment_method" TEXT,
    "card_number" TEXT,
    "card_expiry" TEXT,
    "coupon_code" TEXT
);


-- ════ https://demo-shop.example.com/login ════

CREATE TABLE "Login" (
    "email" VARCHAR,
    "password" TEXT,
    "remember_me" BOOLEAN
);

CREATE TABLE "Registration" (
    "reg_name" TEXT,
    "reg_email" VARCHAR,
    "reg_password" TEXT,
    "reg_password_confirm" TEXT,
    "reg_phone" TEXT,
    "agree_terms" BOOLEAN
);
