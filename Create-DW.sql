-- #####################################################################
-- ## FILE: Create-DW.sql
-- ##
-- ## This schema is a "Galaxy Schema" (a Star Schema with multiple
-- ## fact tables or shared dimensions) to correctly model
-- ## Products, Stores, and Suppliers as separate dimensions.
-- #####################################################################

-- Block 1
-- This command deletes the old 'walmart' database if it exists, so we can start fresh.
drop database if exists walmart;

-- Block 2
-- This command creates the new 'walmart' database.
create database if not exists walmart;

-- Block 3
-- This command tells MySQL to use the 'walmart' database for all following commands.
use walmart;

-- Block 4
-- This temporarily turns off key checks so we can drop and create tables without errors.
set foreign_key_checks=0;

-- Table 1: DimDate
-- This table holds all the date information (like month, year, or if it's a weekend).
drop table if exists DimDate;
create table DimDate (
    Date_Key          int primary key,
    Full_Date         date not null,
    Day_Of_Week_Name  varchar(10) not null,
    Day_Of_Week_Num   int not null,
    Is_Weekend        tinyint(1) not null,
    Month_Name        varchar(10) not null,
    Month_Num         int not null,
    Quarter           int not null,
    Year              int not null,
    index idx_dimdate_full_date (Full_Date)
) engine=InnoDB;

-- Table 2: DimCustomer
-- This table stores all the details about each customer (like age, gender, and occupation).
drop table if exists DimCustomer;
create table DimCustomer (
    Customer_ID                 int primary key,
    Age_Group                   varchar(10) not null,
    Gender                      char(1) not null,
    Occupation                  varchar(50) not null,
    City_Category               char(1) not null,
    Stay_In_Current_City_Years  varchar(5) not null,
    Marital_Status              int not null,
    index idx_dimcustomer_city_cat (City_Category),
    index idx_dimcustomer_occupation (Occupation)
) engine=InnoDB;

-- Table 3: DimStore
-- This new table stores the unique ID and name for each store.
drop table if exists DimStore;
create table DimStore (
    Store_ID            varchar(20) primary key, -- From product_master_data.csv
    Store_Name          varchar(100)
) engine=InnoDB;

-- Table 4: DimSupplier
-- This new table stores the unique ID and name for each supplier.
drop table if exists DimSupplier;
create table DimSupplier (
    Supplier_ID         varchar(20) primary key, -- From product_master_data.csv
    Supplier_Name       varchar(100)
) engine=InnoDB;

-- Table 5: DimProduct
-- This table stores details about each product (like its ID and category).
drop table if exists DimProduct;
create table DimProduct (
    Product_ID          varchar(20) primary key,
    Product_Category    varchar(50) not null, -- Renamed from product_category_1
    index idx_dimproduct_cat (Product_Category)
) engine=InnoDB;

-- Table 6: FactSales
-- This is the main table that links all the other tables together for every sale.
drop table if exists FactSales;
create table FactSales (
    Transaction_ID      varchar(50) not null,
    Customer_ID         int not null,
    Product_ID          varchar(20) not null,
    Store_ID            varchar(20) not null, -- NEW
    Supplier_ID         varchar(20) not null, -- NEW
    Date_Key            int not null,
    Price               decimal(10, 2) not null, -- NEW (Price at time of sale)
    Quantity            int not null,            -- NEW (Better to store this)
    Purchase_Amount     decimal(12, 2) not null, -- (Price * Quantity)

    -- A composite key is needed
    primary key (Transaction_ID, Product_ID, Store_ID), 
    
    -- Foreign Key constraints
    constraint fk_customer
        foreign key(Customer_ID) references DimCustomer(Customer_ID),
    constraint fk_product
        foreign key(Product_ID) references DimProduct(Product_ID),
    constraint fk_store
        foreign key(Store_ID) references DimStore(Store_ID),
    constraint fk_supplier
        foreign key(Supplier_ID) references DimSupplier(Supplier_ID),
    constraint fk_date
        foreign key(Date_Key) references DimDate(Date_Key),
        
    index idx_factsales_date_key (Date_Key),
    index idx_factsales_cust_prod (Customer_ID, Product_ID),
    index idx_factsales_store_supp (Store_ID, Supplier_ID)
) engine=InnoDB;

-- Block 5
-- This turns the foreign key checks back on.
set foreign_key_checks=1;

-- Query 1
-- This shows everything in the product table.
select * from dimproduct;

-- Query 2
-- This shows everything in the date table.
select * from dimdate;

-- Query 3
-- This shows everything in the customer table.
select * from dimcustomer;

-- Query 4
-- This shows everything in the store table.
select * from dimstore;

-- Query 5
-- This shows everything in the supplier table.
select * from dimsupplier;

-- Query 6
-- This shows everything in the main sales table.
select * from factsales;

-- Query 7
-- This counts how many rows are in the main sales table.
select count(*) from factsales;