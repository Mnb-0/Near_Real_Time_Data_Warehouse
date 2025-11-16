-- #####################################################################
-- ## FILE: Create-DW.sql
-- ##
-- ## This schema is a "Galaxy Schema" (a Star Schema with multiple
-- ## fact tables or shared dimensions) to correctly model
-- ## Products, Stores, and Suppliers as separate dimensions.
-- #####################################################################

DROP DATABASE IF EXISTS walmart;
CREATE DATABASE IF NOT EXISTS walmart;
USE walmart;

SET FOREIGN_KEY_CHECKS=0;

-- ##
-- ## Dimension: DimDate
-- ##
DROP TABLE IF EXISTS DimDate;
CREATE TABLE DimDate (
    Date_Key          INT PRIMARY KEY,
    Full_Date         DATE NOT NULL,
    Day_Of_Week_Name  VARCHAR(10) NOT NULL,
    Day_Of_Week_Num   INT NOT NULL,
    Is_Weekend        TINYINT(1) NOT NULL,
    Month_Name        VARCHAR(10) NOT NULL,
    Month_Num         INT NOT NULL,
    Quarter           INT NOT NULL,
    Year              INT NOT NULL,
    INDEX idx_dimdate_full_date (Full_Date)
) ENGINE=InnoDB;

-- ##
-- ## Dimension: DimCustomer
-- ##
DROP TABLE IF EXISTS DimCustomer;
CREATE TABLE DimCustomer (
    Customer_ID                 INT PRIMARY KEY,
    Age_Group                   VARCHAR(10) NOT NULL,
    Gender                      CHAR(1) NOT NULL,
    Occupation                  VARCHAR(50) NOT NULL,
    City_Category               CHAR(1) NOT NULL,
    Stay_In_Current_City_Years  VARCHAR(5) NOT NULL,
    Marital_Status              INT NOT NULL,
    INDEX idx_dimcustomer_city_cat (City_Category),
    INDEX idx_dimcustomer_occupation (Occupation)
) ENGINE=InnoDB;

-- ##
-- ## Dimension: DimStore (NEW)
-- ## This new table stores store information.
-- ##
DROP TABLE IF EXISTS DimStore;
CREATE TABLE DimStore (
    Store_ID            VARCHAR(20) PRIMARY KEY, -- From product_master_data.csv
    Store_Name          VARCHAR(100)
) ENGINE=InnoDB;

-- ##
-- ## Dimension: DimSupplier (NEW)
-- ## This new table stores supplier information.
-- ##
DROP TABLE IF EXISTS DimSupplier;
CREATE TABLE DimSupplier (
    Supplier_ID         VARCHAR(20) PRIMARY KEY, -- From product_master_data.csv
    Supplier_Name       VARCHAR(100)
) ENGINE=InnoDB;

-- ##
-- ## Dimension: DimProduct (MODIFIED)
-- ## This table now holds ONLY product-specific attributes.
-- ## Price, Store, and Supplier have been moved.
-- ##
DROP TABLE IF EXISTS DimProduct;
CREATE TABLE DimProduct (
    Product_ID          VARCHAR(20) PRIMARY KEY,
    Product_Category    VARCHAR(50) NOT NULL, -- Renamed from product_category_1
    INDEX idx_dimproduct_cat (Product_Category)
) ENGINE=InnoDB;

-- ##
-- ## Fact Table: FactSales (MODIFIED)
-- ## This table is now much larger. It links to all dimensions
-- ## and stores the price that was used for the transaction.
-- ##
DROP TABLE IF EXISTS FactSales;
CREATE TABLE FactSales (
    Transaction_ID      VARCHAR(50) NOT NULL,
    Customer_ID         INT NOT NULL,
    Product_ID          VARCHAR(20) NOT NULL,
    Store_ID            VARCHAR(20) NOT NULL, -- NEW
    Supplier_ID         VARCHAR(20) NOT NULL, -- NEW
    Date_Key            INT NOT NULL,
    Price               DECIMAL(10, 2) NOT NULL, -- NEW (Price at time of sale)
    Quantity            INT NOT NULL,            -- NEW (Better to store this)
    Purchase_Amount     DECIMAL(12, 2) NOT NULL, -- (Price * Quantity)

    -- A composite key is needed
    PRIMARY KEY (Transaction_ID, Product_ID, Store_ID), 
    
    -- Foreign Key constraints
    CONSTRAINT fk_customer
        FOREIGN KEY(Customer_ID) REFERENCES DimCustomer(Customer_ID),
    CONSTRAINT fk_product
        FOREIGN KEY(Product_ID) REFERENCES DimProduct(Product_ID),
    CONSTRAINT fk_store
        FOREIGN KEY(Store_ID) REFERENCES DimStore(Store_ID),
    CONSTRAINT fk_supplier
        FOREIGN KEY(Supplier_ID) REFERENCES DimSupplier(Supplier_ID),
    CONSTRAINT fk_date
        FOREIGN KEY(Date_Key) REFERENCES DimDate(Date_Key),
        
    INDEX idx_factsales_date_key (Date_Key),
    INDEX idx_factsales_cust_prod (Customer_ID, Product_ID),
    INDEX idx_factsales_store_supp (Store_ID, Supplier_ID)
) ENGINE=InnoDB;

SET FOREIGN_KEY_CHECKS=1;

select * from dimproduct;
select * from dimdate;
select * from dimcustomer;
select * from factsales;
select count(*) from factsales;
