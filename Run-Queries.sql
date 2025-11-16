-- #####################################################################
-- ## FILE: Run-Queries.sql (CORRECTED)
-- ##
-- ## This script is now consistent with the new schema.
-- ## 1. The View joins all 5 dimension tables.
-- ## 2. Column names (e.g., product_category) are fixed.
-- ## 3. Queries (Q12, Q13, etc.) now use the correct Store/Supplier data.
-- #####################################################################
USE walmart;

-- ##
-- ## Helper View (MODIFIED)
-- ## This view now joins all tables, providing a complete analytical base.
-- ##
CREATE OR REPLACE VIEW v_SalesAnalysis AS
SELECT
    f.Transaction_ID,
    f.Quantity,
    f.Price,
    f.Purchase_Amount,
    
    -- Date Attributes
    d.Full_Date, d.Day_Of_Week_Name, d.Is_Weekend, 
    d.Month_Name, d.Month_Num, d.Quarter, d.Year,
    
    -- Customer Attributes
    c.Customer_ID, c.Age_Group, c.Gender, c.Occupation, 
    c.City_Category, c.Stay_In_Current_City_Years, c.Marital_Status,
    
    -- Product Attributes
    p.Product_ID, 
    p.Product_Category, -- <-- FIX: Renamed from product_category_1
    
    -- Store Attributes
    s.Store_ID,
    s.Store_Name,
    
    -- Supplier Attributes
    sp.Supplier_ID,
    sp.Supplier_Name
FROM
    FactSales f
JOIN
    DimDate d ON f.Date_Key = d.Date_Key
JOIN
    DimCustomer c ON f.Customer_ID = c.Customer_ID
JOIN
    DimProduct p ON f.Product_ID = p.Product_ID
JOIN
    DimStore s ON f.Store_ID = s.Store_ID
JOIN
    DimSupplier sp ON f.Supplier_ID = sp.Supplier_ID;

---
-- Q1 & Q11. Top 5 Revenue-Generating Products (Weekday/Weekend, Monthly)
---
WITH RankedProducts AS (
    SELECT
        v.Year,
        v.Month_Name,
        CASE WHEN v.Is_Weekend = 1 THEN 'Weekend' ELSE 'Weekday' END AS Day_Type,
        v.Product_ID,
        SUM(v.Purchase_Amount) AS Total_Revenue,
        ROW_NUMBER() OVER(
            PARTITION BY v.Year, v.Month_Num, v.Is_Weekend 
            ORDER BY SUM(v.Purchase_Amount) DESC
        ) AS RankNum
    FROM
        v_SalesAnalysis v
    WHERE
        v.Year = 2019 -- Example Year
    GROUP BY
        v.Year, v.Month_Name, v.Month_Num, v.Is_Weekend, v.Product_ID
)
SELECT
    Year, Month_Name, Day_Type, Product_ID, Total_Revenue, RankNum
FROM
    RankedProducts
WHERE
    RankNum <= 5
ORDER BY
    Year, Month_Name, Day_Type, RankNum;

---
-- Q2. Customer Demographics by Purchase Amount (by City Category)
---
SELECT
    City_Category,
    Gender,
    Age_Group,
    SUM(Purchase_Amount) AS Total_Purchase_Amount,
    COUNT(DISTINCT Customer_ID) AS Total_Customers
FROM
    v_SalesAnalysis
GROUP BY
    City_Category, Gender, Age_Group
ORDER BY
    City_Category, Total_Purchase_Amount DESC;

---
-- Q3. Product Category Sales by Occupation
---
SELECT
    Occupation,
    Product_Category, -- <-- FIX: Renamed from product_category_1
    SUM(Purchase_Amount) AS Total_Sales
FROM
    v_SalesAnalysis
GROUP BY
    Occupation, Product_Category
ORDER BY
    Occupation, Total_Sales DESC;

---
-- Q4. Total Purchases by Gender and Age Group (Quarterly Trend)
---
SELECT
    Quarter,
    Gender,
    Age_Group,
    SUM(Purchase_Amount) AS Total_Purchases
FROM
    v_SalesAnalysis
WHERE
    Year = 2019 -- Example: "current year"
GROUP BY
    Quarter, Gender, Age_Group
ORDER BY
    Quarter, Gender, Age_Group;

---
-- Q5. Top 5 Occupations by Product Category Sales
---
WITH RankedOccupations AS (
    SELECT
        Product_Category, -- <-- FIX: Renamed from product_category_1
        Occupation,
        SUM(Purchase_Amount) AS Total_Sales,
        ROW_NUMBER() OVER(
            PARTITION BY Product_Category 
            ORDER BY SUM(Purchase_Amount) DESC
        ) AS RankNum
    FROM
        v_SalesAnalysis
    GROUP BY
        Product_Category, Occupation
)
SELECT
    Product_Category, Occupation, Total_Sales
FROM
    RankedOccupations
WHERE
    RankNum <= 5
ORDER BY
    Product_Category, RankNum;

---
-- Q6. City Category Performance by Marital Status (Monthly, Past 6 Months)
---
SELECT
    Year,
    Month_Name,
    City_Category,
    CASE WHEN Marital_Status = 1 THEN 'Married' ELSE 'Single' END AS Marital_Status,
    SUM(Purchase_Amount) AS Total_Purchases
FROM
    v_SalesAnalysis
WHERE
    Full_Date BETWEEN '2019-01-01' AND '2019-06-30' -- Example time window
GROUP BY
    Year, Month_Num, Month_Name, City_Category, Marital_Status
ORDER BY
    Year, Month_Num, City_Category;

---
-- Q7. Average Purchase Amount by Stay Duration and Gender
---
SELECT
    Stay_In_Current_City_Years,
    Gender,
    AVG(Purchase_Amount) AS Average_Purchase_Amount
FROM
    v_SalesAnalysis
GROUP BY
    Stay_In_Current_City_Years, Gender
ORDER BY
    Stay_In_Current_City_Years, Gender;

---
-- Q8. Top 5 Revenue-Generating Cities by Product Category
---
WITH RankedCities AS (
    SELECT
        Product_Category, -- <-- FIX: Renamed from product_category_1
        City_Category,
        SUM(Purchase_Amount) AS Total_Revenue,
        ROW_NUMBER() OVER(
            PARTITION BY Product_Category
            ORDER BY SUM(Purchase_Amount) DESC
        ) AS RankNum
    FROM
        v_SalesAnalysis
    GROUP BY
        Product_Category, City_Category
)
SELECT
    Product_Category, City_Category, Total_Revenue
FROM
    RankedCities
WHERE
    RankNum <= 5
ORDER BY
    Product_Category, RankNum;

---
-- Q9. Monthly Sales Growth by Product Category
---
WITH MonthlySales AS (
    SELECT
        Product_Category, -- <-- FIX: Renamed from product_category_1
        Year,
        Month_Num,
        SUM(Purchase_Amount) AS Current_Month_Sales
    FROM
        v_SalesAnalysis
    WHERE
        Year = 2019 -- Example: "current year"
    GROUP BY
        Product_Category, Year, Month_Num
),
LaggedSales AS (
    SELECT
        Product_Category,
        Year,
        Month_Num,
        Current_Month_Sales,
        LAG(Current_Month_Sales, 1, 0) OVER(
            PARTITION BY Product_Category
            ORDER BY Year, Month_Num
        ) AS Previous_Month_Sales
    FROM
        MonthlySales
)
SELECT
    Product_Category,
    Year,
    Month_Num,
    Current_Month_Sales,
    Previous_Month_Sales,
    CASE
        WHEN Previous_Month_Sales = 0 THEN NULL
        ELSE (Current_Month_Sales - Previous_Month_Sales) * 100.0 / Previous_Month_Sales
    END AS MoM_Growth_Percentage
FROM
    LaggedSales
ORDER BY
    Product_Category, Year, Month_Num;

---
-- Q10. Weekend vs. Weekday Sales by Age Group
---
SELECT
    Age_Group,
    CASE WHEN Is_Weekend = 1 THEN 'Weekend' ELSE 'Weekday' END AS Day_Type,
    SUM(Purchase_Amount) AS Total_Sales
FROM
    v_SalesAnalysis
WHERE
    Year = 2019 -- Example: "current year"
GROUP BY
    Age_Group, Is_Weekend
ORDER BY
    Age_Group, Day_Type;

---
-- Q12. Trend Analysis of Store Revenue Growth Rate (Quarterly, 2017)
-- <-- FIX: Now correctly uses Store_Name -->
---
WITH QuarterlySales AS (
    SELECT
        Store_Name, -- <-- CORRECTED
        Quarter,
        SUM(Purchase_Amount) AS Current_Quarter_Sales
    FROM
        v_SalesAnalysis
    WHERE
        Year = 2017 -- Per query spec
    GROUP BY
        Store_Name, Quarter
),
LaggedQuarterlySales AS (
    SELECT
        Store_Name,
        Quarter,
        Current_Quarter_Sales,
        LAG(Current_Quarter_Sales, 1, 0) OVER(
            PARTITION BY Store_Name
            ORDER BY Quarter
        ) AS Previous_Quarter_Sales
    FROM
        QuarterlySales
)
SELECT
    Store_Name,
    Quarter,
    Current_Quarter_Sales,
    Previous_Quarter_Sales,
    CASE
        WHEN Previous_Quarter_Sales = 0 THEN NULL
        ELSE (Current_Quarter_Sales - Previous_Quarter_Sales) * 100.0 / Previous_Quarter_Sales
    END AS QoQ_Growth_Percentage
FROM
    LaggedQuarterlySales
ORDER BY
    Store_Name, Quarter;

---
-- Q13. Detailed Supplier Sales Contribution by Store and Product Name
-- <-- FIX: Now correctly uses Store, Supplier, and Product -->
---
SELECT
    Store_Name,
    Supplier_Name,
    Product_ID,       -- Per query spec "Product Name"
    Product_Category, -- <-- FIX: Renamed from product_category_1
    SUM(Purchase_Amount) AS Total_Sales
FROM
    v_SalesAnalysis
GROUP BY
    Store_Name, Supplier_Name, Product_ID, Product_Category
ORDER BY
    Store_Name, Supplier_Name, Total_Sales DESC;

---
-- Q14. Seasonal Analysis of Product Sales
---
SELECT
    Product_ID,
    CASE 
        WHEN Month_Num IN (3, 4, 5) THEN 'Spring'
        WHEN Month_Num IN (6, 7, 8) THEN 'Summer'
        WHEN Month_Num IN (9, 10, 11) THEN 'Fall'
        ELSE 'Winter' -- (12, 1, 2)
    END AS Season,
    SUM(Purchase_Amount) AS Total_Sales
FROM
    v_SalesAnalysis
GROUP BY
    Product_ID, Season
ORDER BY
    Product_ID, Season;

---
-- Q15. Store-Wise and Supplier-Wise Monthly Revenue Volatility
-- <-- FIX: Now correctly uses Store_Name and Supplier_Name -->
---
WITH MonthlySales AS (
    SELECT
        Store_Name,
        Supplier_Name,
        Year,
        Month_Num,
        SUM(Purchase_Amount) AS Current_Month_Sales
    FROM
        v_SalesAnalysis
    GROUP BY
        Store_Name, Supplier_Name, Year, Month_Num
),
LaggedSales AS (
    SELECT
        Store_Name,
        Supplier_Name,
        Year,
        Month_Num,
        Current_Month_Sales,
        LAG(Current_Month_Sales, 1, 0) OVER(
            PARTITION BY Store_Name, Supplier_Name
            ORDER BY Year, Month_Num
        ) AS Previous_Month_Sales
    FROM
        MonthlySales
)
SELECT
    Store_Name,
    Supplier_Name,
    Year,
    Month_Num,
    Current_Month_Sales,
    Previous_Month_Sales,
    CASE
        WHEN Previous_Month_Sales = 0 THEN NULL
        ELSE (Current_Month_Sales - Previous_Month_Sales) * 100.0 / Previous_Month_Sales
    END AS MoM_Volatility_Percent
FROM
    LaggedSales
ORDER BY
    Store_Name, Supplier_Name, Year, Month_Num;

---
-- Q16. Top 5 Products Purchased Together (Product Affinity Analysis)
---
SELECT
    f1.Product_ID AS Product_A,
    f2.Product_ID AS Product_B,
    COUNT(*) AS Times_Purchased_Together
FROM
    FactSales f1
JOIN
    FactSales f2 
    ON f1.Transaction_ID = f2.Transaction_ID
    AND f1.Product_ID < f2.Product_ID -- Prevents (A,A) and (B,A) pairs
GROUP BY
    f1.Product_ID, f2.Product_ID
ORDER BY
    Times_Purchased_Together DESC
LIMIT 5;

---
-- Q17. Yearly Revenue Trends by Store, Supplier, and Product with ROLLUP
-- <-- FIX: Now correctly uses Store, Supplier, and Product -->
---
SELECT
    Year,
    Store_Name,
    Supplier_Name,
    Product_Category, -- <-- FIX: Renamed from product_category_1
    Product_ID,
    SUM(Purchase_Amount) AS Total_Revenue
FROM
    v_SalesAnalysis
GROUP BY
    Year, Store_Name, Supplier_Name, Product_Category, Product_ID WITH ROLLUP
ORDER BY
    Year, Store_Name, Supplier_Name, Product_Category, Product_ID;

---
-- Q18. Revenue and Volume-Based Sales (H1 vs H2)
---
SELECT
    Year,
    Product_ID,
    -- H1 Revenue (Q1 + Q2)
    SUM(CASE WHEN Quarter IN (1, 2) THEN Purchase_Amount ELSE 0 END) AS H1_Revenue,
    -- H2 Revenue (Q3 + Q4)
    SUM(CASE WHEN Quarter IN (3, 4) THEN Purchase_Amount ELSE 0 END) AS H2_Revenue,
    -- H1 Volume
    SUM(CASE WHEN Quarter IN (1, 2) THEN Quantity ELSE 0 END) AS H1_Volume,
    -- H2 Volume
    SUM(CASE WHEN Quarter IN (3, 4) THEN Quantity ELSE 0 END) AS H2_Volume,
    -- Yearly Totals
    SUM(Purchase_Amount) AS Total_Yearly_Revenue,
    SUM(Quantity) AS Total_Yearly_Volume
FROM
    v_SalesAnalysis
GROUP BY
    Year, Product_ID
ORDER BY
    Year, Total_Yearly_Revenue DESC;

---
-- Q19. Identify High Revenue Spikes (Outliers)
---
WITH DailyProductSales AS (
    SELECT
        Product_ID,
        Full_Date,
        SUM(Purchase_Amount) AS Daily_Sales
    FROM
        v_SalesAnalysis
    GROUP BY
        Product_ID, Full_Date
),
ProductAverages AS (
    SELECT
        Product_ID,
        Full_Date,
        Daily_Sales,
        AVG(Daily_Sales) OVER(PARTITION BY Product_ID) AS Avg_Daily_Sales
    FROM
        DailyProductSales
)
SELECT
    Product_ID,
    Full_Date,
    Daily_Sales,
    Avg_Daily_Sales
FROM
    ProductAverages
WHERE
    Daily_Sales > (Avg_Daily_Sales * 2) -- Spike > 2x average
ORDER BY
    Product_ID, Full_Date;

---
-- Q20. Create a View for Optimized Sales Analysis
-- <-- FIX: Now correctly uses Store_Name -->
---
CREATE OR REPLACE VIEW v_Store_Quarterly_Sales AS
SELECT
    Store_Name,
    Year,
    Quarter,
    SUM(Purchase_Amount) AS Total_Quarterly_Sales
FROM
    v_SalesAnalysis
GROUP BY
    Store_Name, Year, Quarter
ORDER BY
    Store_Name, Year, Quarter;