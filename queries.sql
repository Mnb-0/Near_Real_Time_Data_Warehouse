-- #####################################################################
-- ## Helper View: v_SalesAnalysis
-- ## Creates a single, joined view of all tables for easy querying.
-- #####################################################################
use walmart;
CREATE OR REPLACE VIEW v_SalesAnalysis AS
SELECT
    f.Transaction_ID,
    f.Purchase_Amount,
    d.Full_Date,
    d.Day_Of_Week_Name,
    d.Is_Weekend, -- 0 (Weekday) or 1 (Weekend)
    d.Month_Name,
    d.Month_Num,
    d.Quarter,
    d.Year,
    c.Customer_ID,
    c.Age_Group,
    c.Gender,
    c.Occupation,
    c.City_Category,
    c.Stay_In_Current_City_Years,
    c.Marital_Status, -- 0 (Single) or 1 (Married)
    p.Product_ID,
    p.Product_Category_1
FROM
    FactSales f
JOIN
    DimDate d ON f.Date_Key = d.Date_Key
JOIN
    DimCustomer c ON f.Customer_ID = c.Customer_ID
JOIN
    DimProduct p ON f.Product_ID = p.Product_ID;
    
-- Q1, Q11 (Same)
-- This query ranks the top 5 products, partitioning the data by year, 
-- month, and whether the day was a weekday or weekend.
WITH RankedProducts AS (
    SELECT
        v.Year,
        v.Month_Name,
        CASE WHEN v.Is_Weekend = 1 THEN 'Weekend' ELSE 'Weekday' END AS Day_Type,
        v.Product_ID,
        SUM(v.Purchase_Amount) AS Total_Revenue,
        -- Rank products within each group
        ROW_NUMBER() OVER(
            PARTITION BY v.Year, v.Month_Num, v.Is_Weekend 
            ORDER BY SUM(v.Purchase_Amount) DESC
        ) AS RankNum
    FROM
        v_SalesAnalysis v
    WHERE
        v.Year = 2019 -- Example: Specify a year
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
    
    
-- Q2
-- This query provides a simple breakdown of total spending by
-- the key demographic segments: city, gender, and age.
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
    
-- Q3
-- This query links customer occupation directly to product categories
-- to see which professions buy which types of goods.
SELECT
    Occupation,
    Product_Category_1,
    SUM(Purchase_Amount) AS Total_Sales
FROM
    v_SalesAnalysis
GROUP BY
    Occupation, Product_Category_1
ORDER BY
    Occupation, Total_Sales DESC;
    
-- Q4
-- This query tracks spending habits of demographic groups over time (quarterly)
-- for the specified "current year".
SELECT
    Quarter,
    Gender,
    Age_Group,
    SUM(Purchase_Amount) AS Total_Purchases
FROM
    v_SalesAnalysis
WHERE
    Year = 2019 
GROUP BY
    Quarter, Gender, Age_Group
ORDER BY
    Quarter, Gender, Age_Group;
    
-- Q5
-- This is the inverse of Q3. It ranks the top 5 professions
-- for each product category.
WITH RankedOccupations AS (
    SELECT
        Product_Category_1,
        Occupation,
        SUM(Purchase_Amount) AS Total_Sales,
        ROW_NUMBER() OVER(
            PARTITION BY Product_Category_1 
            ORDER BY SUM(Purchase_Amount) DESC
        ) AS RankNum
    FROM
        v_SalesAnalysis
    GROUP BY
        Product_Category_1, Occupation
)
SELECT
    Product_Category_1, Occupation, Total_Sales
FROM
    RankedOccupations
WHERE
    RankNum <= 5
ORDER BY
    Product_Category_1, RankNum;
    
-- Q6
-- This query filters for a specific time window (e.g., first 6 months
-- of 2024) to analyze spending by city and marital status.
SELECT
    Year,
    Month_Name,
    City_Category,
    CASE WHEN Marital_Status = 1 THEN 'Married' ELSE 'Single' END AS Marital_Status,
    SUM(Purchase_Amount) AS Total_Purchases
FROM
    v_SalesAnalysis
WHERE
    -- Example: "past 6 months" from a fixed date for reliable results
    Full_Date BETWEEN '2019-01-01' AND '2019-06-30'
GROUP BY
    Year, Month_Num, Month_Name, City_Category, Marital_Status
ORDER BY
    Year, Month_Num, City_Category;
    
-- Q7
-- This calculates the average *transaction value* (not total sales)
-- based on customer tenure in a city and their gender.
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
    
-- Q8
-- This query identifies the most valuable cities for each product category.
WITH RankedCities AS (
    SELECT
        Product_Category_1,
        City_Category,
        SUM(Purchase_Amount) AS Total_Revenue,
        ROW_NUMBER() OVER(
            PARTITION BY Product_Category_1
            ORDER BY SUM(Purchase_Amount) DESC
        ) AS RankNum
    FROM
        v_SalesAnalysis
    GROUP BY
        Product_Category_1, City_Category
)
SELECT
    Product_Category_1, City_Category, Total_Revenue
FROM
    RankedCities
WHERE
    RankNum <= 5 -- This will show the top 3 since only A, B, C exist
ORDER BY
    Product_Category_1, RankNum;
    
-- Q9
-- This query uses the LAG() window function to compare one month's sales
-- to the previous month's sales, calculating the % change.
WITH MonthlySales AS (
    -- Step 1: Get total sales for each category, each month
    SELECT
        Product_Category_1,
        Year,
        Month_Num,
        SUM(Purchase_Amount) AS Current_Month_Sales
    FROM
        v_SalesAnalysis
    WHERE
        Year = 2019 -- For "current year"
    GROUP BY
        Product_Category_1, Year, Month_Num
),
LaggedSales AS (
    -- Step 2: Use LAG() to get the *previous* month's sales
    SELECT
        Product_Category_1,
        Year,
        Month_Num,
        Current_Month_Sales,
        LAG(Current_Month_Sales, 1, 0) OVER(
            PARTITION BY Product_Category_1
            ORDER BY Year, Month_Num
        ) AS Previous_Month_Sales
    FROM
        MonthlySales
)
-- Step 3: Calculate the growth percentage
SELECT
    Product_Category_1,
    Year,
    Month_Num,
    Current_Month_Sales,
    Previous_Month_Sales,
    CASE
        WHEN Previous_Month_Sales = 0 THEN NULL -- Avoid divide-by-zero
        ELSE (Current_Month_Sales - Previous_Month_Sales) * 100.0 / Previous_Month_Sales
    END AS MoM_Growth_Percentage
FROM
    LaggedSales
ORDER BY
    Product_Category_1, Year, Month_Num;
    
-- Q10
-- A simple comparison of spending habits based on day type.
SELECT
    Age_Group,
    CASE WHEN Is_Weekend = 1 THEN 'Weekend' ELSE 'Weekday' END AS Day_Type,
    SUM(Purchase_Amount) AS Total_Sales
FROM
    v_SalesAnalysis
WHERE
    Year = 2019 -- For "current year"
GROUP BY
    Age_Group, Is_Weekend
ORDER BY
    Age_Group, Day_Type;
    
-- Q12
-- This logic is similar to Q9, but adapted for quarterly data
-- and for City_Category instead of Product.
WITH QuarterlySales AS (
    SELECT
        City_Category,
        Quarter,
        SUM(Purchase_Amount) AS Current_Quarter_Sales
    FROM
        v_SalesAnalysis
    WHERE
        Year = 2019
    GROUP BY
        City_Category, Quarter
),
LaggedQuarterlySales AS (
    SELECT
        City_Category,
        Quarter,
        Current_Quarter_Sales,
        -- Get the previous quarter's sales for the same city
        LAG(Current_Quarter_Sales, 1, 0) OVER(
            PARTITION BY City_Category
            ORDER BY Quarter
        ) AS Previous_Quarter_Sales
    FROM
        QuarterlySales
)
SELECT
    City_Category,
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
    City_Category, Quarter;
    
-- Q13
-- This query is adapted to show:
-- "City_Category Sales Contribution by Product_ID"
SELECT
    City_Category,
    Product_ID,
    Product_Category_1,
    SUM(Purchase_Amount) AS Total_Sales
FROM
    v_SalesAnalysis
GROUP BY
    City_Category, Product_ID, Product_Category_1
ORDER BY
    City_Category, Product_ID;
    
-- Q14
-- This query uses a CASE statement to group months into
-- standard meteorological seasons.
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
    
-- Q15
-- This query (like Q9) finds the month-over-month % change,
-- but for the City/Product_Category grain.
WITH MonthlySales AS (
    SELECT
        City_Category,
        Product_Category_1,
        Year,
        Month_Num,
        SUM(Purchase_Amount) AS Current_Month_Sales
    FROM
        v_SalesAnalysis
    GROUP BY
        City_Category, Product_Category_1, Year, Month_Num
),
LaggedSales AS (
    SELECT
        City_Category,
        Product_Category_1,
        Year,
        Month_Num,
        Current_Month_Sales,
        LAG(Current_Month_Sales, 1, 0) OVER(
            PARTITION BY City_Category, Product_Category_1
            ORDER BY Year, Month_Num
        ) AS Previous_Month_Sales
    FROM
        MonthlySales
)
SELECT
    City_Category,
    Product_Category_1,
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
    City_Category, Product_Category_1, Year, Month_Num;
    
-- Q16
-- This query self-joins the FactSales table to find pairs of
-- products that appear on the same Transaction_ID.
SELECT
    f1.Product_ID AS Product_A,
    f2.Product_ID AS Product_B,
    COUNT(*) AS Times_Purchased_Together
FROM
    FactSales f1
JOIN
    FactSales f2 
    -- Join on the same transaction
    ON f1.Transaction_ID = f2.Transaction_ID
    -- Use < to ensure (A,B) is counted, but (B,A) and (A,A) are not.
    AND f1.Product_ID < f2.Product_ID 
GROUP BY
    f1.Product_ID, f2.Product_ID
ORDER BY
    Times_Purchased_Together DESC
LIMIT 5;

-- Q17
-- This query uses ROLLUP to generate hierarchical subtotals.
-- It will show totals for (Year, City, Category, Product),
-- then (Year, City, Category), then (Year, City), then (Year),
-- and finally a grand total.
SELECT
    Year,
    City_Category,
    Product_Category_1,
    Product_ID,
    SUM(Purchase_Amount) AS Total_Revenue
FROM
    v_SalesAnalysis
GROUP BY
    Year, City_Category, Product_Category_1, Product_ID WITH ROLLUP
ORDER BY
    Year, City_Category, Product_Category_1, Product_ID;
    
-- Q18
-- This uses conditional aggregation to pivot sales data for
-- the first half (H1) and second half (H2) of the year.
SELECT
    Year,
    Product_ID,
    -- H1 Revenue (Q1 + Q2)
    SUM(CASE WHEN Quarter IN (1, 2) THEN Purchase_Amount ELSE 0 END) AS H1_Revenue,
    -- H2 Revenue (Q3 + Q4)
    SUM(CASE WHEN Quarter IN (3, 4) THEN Purchase_Amount ELSE 0 END) AS H2_Revenue,
    -- H1 Volume
    COUNT(CASE WHEN Quarter IN (1, 2) THEN Transaction_ID ELSE NULL END) AS H1_Volume,
    -- H2 Volume
    COUNT(CASE WHEN Quarter IN (3, 4) THEN Transaction_ID ELSE NULL END) AS H2_Volume,
    -- Yearly Totals
    SUM(Purchase_Amount) AS Total_Yearly_Revenue,
    COUNT(Transaction_ID) AS Total_Yearly_Volume
FROM
    v_SalesAnalysis
GROUP BY
    Year, Product_ID
ORDER BY
    Year, Total_Yearly_Revenue DESC;
    
-- Q19
-- This query finds the long-term average daily sales for a product,
-- then compares each day's sales to that average to find spikes.
WITH DailyProductSales AS (
    -- Step 1: Get total sales for each product on each day
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
    -- Step 2: Calculate the average daily sales for each product
    SELECT
        Product_ID,
        Full_Date,
        Daily_Sales,
        AVG(Daily_Sales) OVER(PARTITION BY Product_ID) AS Avg_Daily_Sales
    FROM
        DailyProductSales
)
-- Step 3: Find days where sales were > 2x the average
SELECT
    Product_ID,
    Full_Date,
    Daily_Sales,
    Avg_Daily_Sales
FROM
    ProductAverages
WHERE
    Daily_Sales > (Avg_Daily_Sales * 2)
ORDER BY
    Product_ID, Full_Date;
    
-- Q20
CREATE OR REPLACE VIEW v_City_Quarterly_Sales AS
SELECT
    City_Category,
    Year,
    Quarter,
    SUM(Purchase_Amount) AS Total_Quarterly_Sales
FROM
    v_SalesAnalysis
GROUP BY
    City_Category, Year, Quarter
ORDER BY
    City_Category, Year, Quarter;