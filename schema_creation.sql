create database walmart;
use walmart;
-- #####################################################################
-- ## SECTION 1: DATA WAREHOUSE SCHEMA (MySQL DDL)
-- ## Database: MySQL 8.0+
-- #####################################################################

SET FOREIGN_KEY_CHECKS=0; -- Disable checks for clean table drops

-- ##
-- ## Dimension: DimDate
-- ## Holds all date and time attributes.
-- ##
DROP TABLE IF EXISTS DimDate;
CREATE TABLE DimDate (
    Date_Key          INT PRIMARY KEY,     -- e.g., 20251115
    Full_Date         DATE NOT NULL,       -- e.g., '2025-11-15'
    Day_Of_Week_Name  VARCHAR(10) NOT NULL,  -- e.g., 'Saturday'
    Day_Of_Week_Num   INT NOT NULL,        -- 1 (Sun) - 7 (Sat)
    Is_Weekend        TINYINT(1) NOT NULL, -- 0 (False), 1 (True)
    Month_Name        VARCHAR(10) NOT NULL,  -- e.g., 'November'
    Month_Num         INT NOT NULL,        -- 1-12
    Quarter           INT NOT NULL,        -- 1-4
    Year              INT NOT NULL,
    INDEX idx_dimdate_full_date (Full_Date)
) ENGINE=InnoDB;

-- ##
-- ## Dimension: DimCustomer
-- ## Holds all customer demographic and segmentation attributes.
-- ##
DROP TABLE IF EXISTS DimCustomer;
CREATE TABLE DimCustomer (
    Customer_ID                 INT PRIMARY KEY,
    Age_Group                   VARCHAR(10) NOT NULL, -- e.g., '26-35'
    Gender                      CHAR(1) NOT NULL,     -- 'M' or 'F'
    Occupation                  VARCHAR(50) NOT NULL, -- e.g., 'Tech'
    City_Category               CHAR(1) NOT NULL,     -- 'A', 'B', 'C'
    Stay_In_Current_City_Years  VARCHAR(5) NOT NULL,  -- e.g., '2', '4+'
    Marital_Status              INT NOT NULL,       -- 0 (Single), 1 (Married)
    INDEX idx_dimcustomer_city_cat (City_Category),
    INDEX idx_dimcustomer_occupation (Occupation)
) ENGINE=InnoDB;


-- ##
-- ## Dimension: DimProduct
-- ## Holds all product category and hierarchy attributes.
-- ##
DROP TABLE IF EXISTS DimProduct;
CREATE TABLE DimProduct (
    Product_ID          VARCHAR(20) PRIMARY KEY, -- Alphanumeric
    Product_Category_1  VARCHAR(50) NOT NULL,
    Product_Category_2  VARCHAR(50),
    Product_Category_3  VARCHAR(50),
    INDEX idx_dimproduct_cat1 (Product_Category_1)
) ENGINE=InnoDB;


-- ##
-- ## Fact Table: FactSales
-- ## This is the target table for the near-real-time HYBRIDJOIN ETL.
-- ##
DROP TABLE IF EXISTS FactSales;
CREATE TABLE FactSales (
    Transaction_ID      VARCHAR(50) NOT NULL, -- Natural key from source
    Customer_ID         INT NOT NULL,
    Product_ID          VARCHAR(20) NOT NULL,
    Date_Key            INT NOT NULL,
    Purchase_Amount     DECIMAL(12, 2) NOT NULL,

    -- Using Transaction_ID + Product_ID as a composite PK
    PRIMARY KEY (Transaction_ID, Product_ID), 

    -- Foreign Key relationships
    CONSTRAINT fk_customer
        FOREIGN KEY(Customer_ID) 
        REFERENCES DimCustomer(Customer_ID),
    CONSTRAINT fk_product
        FOREIGN KEY(Product_ID) 
        REFERENCES DimProduct(Product_ID),
    CONSTRAINT fk_date
        FOREIGN KEY(Date_Key) 
        REFERENCES DimDate(Date_Key),
        
    INDEX idx_factsales_date_key (Date_Key),
    INDEX idx_factsales_cust_prod (Customer_ID, Product_ID)
) ENGINE=InnoDB;

SET FOREIGN_KEY_CHECKS=1; -- Re-enable checks

select * from DimProduct;
select * from DimDate;
select * from DimCustomer;
select * from FactSales;