-- #####################################################################
-- ## FILE: Run-Queries.sql
-- #####################################################################
use walmart;

-- #####################################################################
-- ## Helper View
-- #####################################################################
create or replace view v_SalesAnalysis as
select
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
    p.Product_Category, 
    
    -- Store Attributes
    s.Store_ID,
    s.Store_Name,
    
    -- Supplier Attributes
    sp.Supplier_ID,
    sp.Supplier_Name
from
    FactSales f
join
    DimDate d on f.Date_Key = d.Date_Key
join
    DimCustomer c on f.Customer_ID = c.Customer_ID
join
    DimProduct p on f.Product_ID = p.Product_ID
join
    DimStore s on f.Store_ID = s.Store_ID
join
    DimSupplier sp on f.Supplier_ID = sp.Supplier_ID;

---
-- Query 1 & 11
-- Top 5 revenue-generating products on weekdays and weekends, with monthly drill-down.
---
with RankedProducts as (
    select
        v.Year,
        v.Month_Name,
        case when v.Is_Weekend = 1 then 'Weekend' else 'Weekday' end as Day_Type,
        v.Product_ID,
        sum(v.Purchase_Amount) as Total_Revenue,
        row_number() over(
            partition by v.Year, v.Month_Num, v.Is_Weekend 
            order by sum(v.Purchase_Amount) desc
        ) as RankNum
    from
        v_SalesAnalysis v
    where
        v.Year = 2019 -- Example Year
    group by
        v.Year, v.Month_Name, v.Month_Num, v.Is_Weekend, v.Product_ID
)
select
    Year, Month_Name, Day_Type, Product_ID, Total_Revenue, RankNum
from
    RankedProducts
where
    RankNum <= 5
order by
    Year, Month_Name, Day_Type, RankNum;

---
-- Query 2
-- Customer demographics by purchase amount, with city category breakdown.
---
select
    City_Category,
    Gender,
    Age_Group,
    sum(Purchase_Amount) as Total_Purchase_Amount,
    count(distinct Customer_ID) as Total_Customers
from
    v_SalesAnalysis
group by
    City_Category, Gender, Age_Group
order by
    City_Category, Total_Purchase_Amount desc;

---
-- Query 3
-- Product category sales by occupation.
---
select
    Occupation,
    Product_Category,
    sum(Purchase_Amount) as Total_Sales
from
    v_SalesAnalysis
group by
    Occupation, Product_Category
order by
    Occupation, Total_Sales desc;

---
-- Query 4
-- Total purchases by gender and age group, with quarterly trend.
---
select
    Quarter,
    Gender,
    Age_Group,
    sum(Purchase_Amount) as Total_Purchases
from
    v_SalesAnalysis
where
    Year = 2019 -- Example: "current year"
group by
    Quarter, Gender, Age_Group
order by
    Quarter, Gender, Age_Group;

---
-- Query 5
-- Top 5 occupations by product category sales.
---
with RankedOccupations as (
    select
        Product_Category, 
        Occupation,
        sum(Purchase_Amount) as Total_Sales,
        row_number() over(
            partition by Product_Category 
            order by sum(Purchase_Amount) desc
        ) as RankNum
    from
        v_SalesAnalysis
    group by
        Product_Category, Occupation
)
select
    Product_Category, Occupation, Total_Sales
from
    RankedOccupations
where
    RankNum <= 5
order by
    Product_Category, RankNum;

---
-- Query 6
-- City category performance by marital status, with monthly breakdown for 6 months.
---
select
    Year,
    Month_Name,
    City_Category,
    case when Marital_Status = 1 then 'Married' else 'Single' end as Marital_Status,
    sum(Purchase_Amount) as Total_Purchases
from
    v_SalesAnalysis
where
    Full_Date between '2019-01-01' and '2019-06-30' -- Example time window
group by
    Year, Month_Num, Month_Name, City_Category, Marital_Status
order by
    Year, Month_Num, City_Category;

---
-- Query 7
-- Average purchase amount by stay duration and gender.
---
select
    Stay_In_Current_City_Years,
    Gender,
    avg(Purchase_Amount) as Average_Purchase_Amount
from
    v_SalesAnalysis
group by
    Stay_In_Current_City_Years, Gender
order by
    Stay_In_Current_City_Years, Gender;

---
-- Query 8
-- Top 5 revenue-generating cities by product category.
---
with RankedCities as (
    select
        Product_Category,
        City_Category,
        sum(Purchase_Amount) as Total_Revenue,
        row_number() over(
            partition by Product_Category
            order by sum(Purchase_Amount) desc
        ) as RankNum
    from
        v_SalesAnalysis
    group by
        Product_Category, City_Category
)
select
    Product_Category, City_Category, Total_Revenue
from
    RankedCities
where
    RankNum <= 5
order by
    Product_Category, RankNum;

---
-- Query 9
-- Monthly sales growth by product category.
---
with MonthlySales as (
    select
        Product_Category,
        Year,
        Month_Num,
        sum(Purchase_Amount) as Current_Month_Sales
    from
        v_SalesAnalysis
    where
        Year = 2019 -- Example: "current year"
    group by
        Product_Category, Year, Month_Num
),
LaggedSales as (
    select
        Product_Category,
        Year,
        Month_Num,
        Current_Month_Sales,
        lag(Current_Month_Sales, 1, 0) over(
            partition by Product_Category
            order by Year, Month_Num
        ) as Previous_Month_Sales
    from
        MonthlySales
)
select
    Product_Category,
    Year,
    Month_Num,
    Current_Month_Sales,
    Previous_Month_Sales,
    case
        when Previous_Month_Sales = 0 then null
        else (Current_Month_Sales - Previous_Month_Sales) * 100.0 / Previous_Month_Sales
    end as MoM_Growth_Percentage
from
    LaggedSales
order by
    Product_Category, Year, Month_Num;

---
-- Query 10
-- Weekend vs. weekday sales by age group.
---
select
    Age_Group,
    case when Is_Weekend = 1 then 'Weekend' else 'Weekday' end as Day_Type,
    sum(Purchase_Amount) as Total_Sales
from
    v_SalesAnalysis
where
    Year = 2019 -- Example: "current year"
group by
    Age_Group, Is_Weekend
order by
    Age_Group, Day_Type;

---
-- Query 12
-- Trend analysis of store revenue growth rate, quarterly for 2017.
---
with QuarterlySales as (
    select
        Store_Name,
        Quarter,
        sum(Purchase_Amount) as Current_Quarter_Sales
    from
        v_SalesAnalysis
    where
        Year = 2017 -- Per query spec
    group by
        Store_Name, Quarter
),
LaggedQuarterlySales as (
    select
        Store_Name,
        Quarter,
        Current_Quarter_Sales,
        lag(Current_Quarter_Sales, 1, 0) over(
            partition by Store_Name
            order by Quarter
        ) as Previous_Quarter_Sales
    from
        QuarterlySales
)
select
    Store_Name,
    Quarter,
    Current_Quarter_Sales,
    Previous_Quarter_Sales,
    case
        when Previous_Quarter_Sales = 0 then null
        else (Current_Quarter_Sales - Previous_Quarter_Sales) * 100.0 / Previous_Quarter_Sales
    end as QoQ_Growth_Percentage
from
    LaggedQuarterlySales
order by
    Store_Name, Quarter;

---
-- Query 13
-- Detailed supplier sales contribution by store and product name.
---
select
    Store_Name,
    Supplier_Name,
    Product_ID,       -- Per query spec "Product Name"
    Product_Category,
    sum(Purchase_Amount) as Total_Sales
from
    v_SalesAnalysis
group by
    Store_Name, Supplier_Name, Product_ID, Product_Category
order by
    Store_Name, Supplier_Name, Total_Sales desc;

---
-- Query 14
-- Seasonal analysis of product sales.
---
select
    Product_ID,
    case 
        when Month_Num in (3, 4, 5) then 'Spring'
        when Month_Num in (6, 7, 8) then 'Summer'
        when Month_Num in (9, 10, 11) then 'Fall'
        else 'Winter' -- (12, 1, 2)
    end as Season,
    sum(Purchase_Amount) as Total_Sales
from
    v_SalesAnalysis
group by
    Product_ID, Season
order by
    Product_ID, Season;

---
-- Query 15
-- Store-wise and supplier-wise monthly revenue volatility.
---
with MonthlySales as (
    select
        Store_Name,
        Supplier_Name,
        Year,
        Month_Num,
        sum(Purchase_Amount) as Current_Month_Sales
    from
        v_SalesAnalysis
    group by
        Store_Name, Supplier_Name, Year, Month_Num
),
LaggedSales as (
    select
        Store_Name,
        Supplier_Name,
        Year,
        Month_Num,
        Current_Month_Sales,
        lag(Current_Month_Sales, 1, 0) over(
            partition by Store_Name, Supplier_Name
            order by Year, Month_Num
        ) as Previous_Month_Sales
    from
        MonthlySales
)
select
    Store_Name,
    Supplier_Name,
    Year,
    Month_Num,
    Current_Month_Sales,
    Previous_Month_Sales,
    case
        when Previous_Month_Sales = 0 then null
        else (Current_Month_Sales - Previous_Month_Sales) * 100.0 / Previous_Month_Sales
    end as MoM_Volatility_Percent
from
    LaggedSales
order by
    Store_Name, Supplier_Name, Year, Month_Num;

---
-- Query 16
-- Top 5 products purchased together (product affinity).
---
select
    f1.Product_ID as Product_A,
    f2.Product_ID as Product_B,
    count(*) as Times_Purchased_Together
from
    FactSales f1
join
    FactSales f2 
    on f1.Transaction_ID = f2.Transaction_ID
    and f1.Product_ID < f2.Product_ID -- Prevents (A,A) and (B,A) pairs
group by
    f1.Product_ID, f2.Product_ID
order by
    Times_Purchased_Together desc
limit 5;

---
-- Query 17
-- Yearly revenue trends by store, supplier, and product, with ROLLUP.
---
select
    Year,
    Store_Name,
    Supplier_Name,
    Product_Category, -- <-- FIX: Renamed from product_category_1
    Product_ID,
    sum(Purchase_Amount) as Total_Revenue
from
    v_SalesAnalysis
group by
    Year, Store_Name, Supplier_Name, Product_Category, Product_ID with rollup
order by
    Year, Store_Name, Supplier_Name, Product_Category, Product_ID;

---
-- Query 18
-- Revenue and volume sales analysis for each product for H1 and H2.
---
select
    Year,
    Product_ID,
    -- H1 Revenue (Q1 + Q2)
    sum(case when Quarter in (1, 2) then Purchase_Amount else 0 end) as H1_Revenue,
    -- H2 Revenue (Q3 + Q4)
    sum(case when Quarter in (3, 4) then Purchase_Amount else 0 end) as H2_Revenue,
    -- H1 Volume
    sum(case when Quarter in (1, 2) then Quantity else 0 end) as H1_Volume,
    -- H2 Volume
    sum(case when Quarter in (3, 4) then Quantity else 0 end) as H2_Volume,
    -- Yearly Totals
    sum(Purchase_Amount) as Total_Yearly_Revenue,
    sum(Quantity) as Total_Yearly_Volume
from
    v_SalesAnalysis
group by
    Year, Product_ID
order by
    Year, Total_Yearly_Revenue desc;

---
-- Query 19
-- Identify high revenue spikes in product sales (outliers).
---
with DailyProductSales as (
    select
        Product_ID,
        Full_Date,
        sum(Purchase_Amount) as Daily_Sales
    from
        v_SalesAnalysis
    group by
        Product_ID, Full_Date
),
ProductAverages as (
    select
        Product_ID,
        Full_Date,
        Daily_Sales,
        avg(Daily_Sales) over(partition by Product_ID) as Avg_Daily_Sales
    from
        DailyProductSales
)
select
    Product_ID,
    Full_Date,
    Daily_Sales,
    Avg_Daily_Sales
from
    ProductAverages
where
    Daily_Sales > (Avg_Daily_Sales * 2) -- Spike > 2x average
order by
    Product_ID, Full_Date;

---
-- Query 20
-- Create a view for optimized store quarterly sales analysis.
---
create or replace view v_Store_Quarterly_Sales as
select
    Store_Name,
    Year,
    Quarter,
    sum(Purchase_Amount) as Total_Quarterly_Sales
from
    v_SalesAnalysis
group by
    Store_Name, Year, Quarter
order by
    Store_Name, Year, Quarter;