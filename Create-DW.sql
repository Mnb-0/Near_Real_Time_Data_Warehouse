-- #####################################################################
-- Setting up the walmart DB from scratch. Clean slate, clean tables.  
-- #####################################################################

-- Block 1
-- Tossing the old database so nothing weird carries over.
drop database if exists walmart;

-- Block 2
-- Making a fresh one.
create database if not exists walmart;

-- Block 3
use walmart;

-- Block 4
-- Turning FK checks off
set foreign_key_checks=0;

-- Table 1: DimDate
-- Just the usual date breakdown so we don’t have to compute it every time.
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
-- Customer details: who they are, where they live, what they're doing.
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
-- Simple lookup for store IDs and their names.
drop table if exists DimStore;
create table DimStore (
    Store_ID            varchar(20) primary key,
    Store_Name          varchar(100)
) engine=InnoDB;

-- Table 4: DimSupplier
-- Same idea as stores, but for suppliers.
drop table if exists DimSupplier;
create table DimSupplier (
    Supplier_ID         varchar(20) primary key,
    Supplier_Name       varchar(100)
) engine=InnoDB;

-- Table 5: DimProduct
-- Product info: ID and category
drop table if exists DimProduct;
create table DimProduct (
    Product_ID          varchar(20) primary key,
    Product_Category    varchar(50) not null,
    index idx_dimproduct_cat (Product_Category)
) engine=InnoDB;

-- Table 6: FactSales
-- The main table where everything meets: customers, products, stores, suppliers, dates.
drop table if exists FactSales;
create table FactSales (
    Transaction_ID      varchar(50) not null,
    Customer_ID         int not null,
    Product_ID          varchar(20) not null,
    Store_ID            varchar(20) not null,
    Supplier_ID         varchar(20) not null,
    Date_Key            int not null,
    Price               decimal(10, 2) not null,
    Quantity            int not null,
    Purchase_Amount     decimal(12, 2) not null,

    primary key (Transaction_ID, Product_ID, Store_ID),

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
set foreign_key_checks=1;
