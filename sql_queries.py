# #####################################################################
# ## FILE: sql_queries.py
# ##
# ## This file stores all 20 analytical queries in a dictionary
# ## for the GUI to use.
# #####################################################################

# NOTE: All keywords are lowercase, as requested.
# All queries are based on the corrected Run-Queries.sql file.

QUERIES = {
    "Q1/Q11: Top 5 Products": """
        with RankedProducts as (
            select
                v.Year, v.Month_Name,
                case when v.Is_Weekend = 1 then 'Weekend' else 'Weekday' end as Day_Type,
                v.Product_ID, sum(v.Purchase_Amount) as Total_Revenue,
                row_number() over(
                    partition by v.Year, v.Month_Num, v.Is_Weekend 
                    order by sum(v.Purchase_Amount) desc
                ) as RankNum
            from v_SalesAnalysis v
            where v.Year = 2019
            group by v.Year, v.Month_Name, v.Month_Num, v.Is_Weekend, v.Product_ID
        )
        select Year, Month_Name, Day_Type, Product_ID, Total_Revenue, RankNum
        from RankedProducts
        where RankNum <= 5
        order by Year, Month_Name, Day_Type, RankNum;
    """,

    "Q2: Demographics by City": """
        select
            City_Category, Gender, Age_Group,
            sum(Purchase_Amount) as Total_Purchase_Amount,
            count(distinct Customer_ID) as Total_Customers
        from v_SalesAnalysis
        group by City_Category, Gender, Age_Group
        order by City_Category, Total_Purchase_Amount desc;
    """,

    "Q3: Category Sales by Occupation": """
        select
            Occupation, Product_Category,
            sum(Purchase_Amount) as Total_Sales
        from v_SalesAnalysis
        group by Occupation, Product_Category
        order by Occupation, Total_Sales desc;
    """,

    "Q4: Quarterly Trend by Demo": """
        select
            Quarter, Gender, Age_Group,
            sum(Purchase_Amount) as Total_Purchases
        from v_SalesAnalysis
        where Year = 2019
        group by Quarter, Gender, Age_Group
        order by Quarter, Gender, Age_Group;
    """,

    "Q5: Top 5 Occupations by Category": """
        with RankedOccupations as (
            select
                Product_Category, Occupation,
                sum(Purchase_Amount) as Total_Sales,
                row_number() over(
                    partition by Product_Category 
                    order by sum(Purchase_Amount) desc
                ) as RankNum
            from v_SalesAnalysis
            group by Product_Category, Occupation
        )
        select Product_Category, Occupation, Total_Sales
        from RankedOccupations
        where RankNum <= 5
        order by Product_Category, RankNum;
    """,

    "Q6: City Perf. by Marital (6-mo)": """
        select
            Year, Month_Name, City_Category,
            case when Marital_Status = 1 then 'Married' else 'Single' end as Marital_Status,
            sum(Purchase_Amount) as Total_Purchases
        from v_SalesAnalysis
        where Full_Date between '2019-01-01' and '2019-06-30'
        group by Year, Month_Num, Month_Name, City_Category, Marital_Status
        order by Year, Month_Num, City_Category;
    """,

    "Q7: Avg Purchase by Stay/Gender": """
        select
            Stay_In_Current_City_Years, Gender,
            avg(Purchase_Amount) as Average_Purchase_Amount
        from v_SalesAnalysis
        group by Stay_In_Current_City_Years, Gender
        order by Stay_In_Current_City_Years, Gender;
    """,

    "Q8: Top 5 Cities by Category": """
        with RankedCities as (
            select
                Product_Category, City_Category,
                sum(Purchase_Amount) as Total_Revenue,
                row_number() over(
                    partition by Product_Category
                    order by sum(Purchase_Amount) desc
                ) as RankNum
            from v_SalesAnalysis
            group by Product_Category, City_Category
        )
        select Product_Category, City_Category, Total_Revenue
        from RankedCities
        where RankNum <= 5
        order by Product_Category, RankNum;
    """,

    "Q9: Monthly Growth by Category": """
        with MonthlySales as (
            select
                Product_Category, Year, Month_Num,
                sum(Purchase_Amount) as Current_Month_Sales
            from v_SalesAnalysis
            where Year = 2019
            group by Product_Category, Year, Month_Num
        ),
        LaggedSales as (
            select
                Product_Category, Year, Month_Num, Current_Month_Sales,
                lag(Current_Month_Sales, 1, 0) over(
                    partition by Product_Category
                    order by Year, Month_Num
                ) as Previous_Month_Sales
            from MonthlySales
        )
        select
            Product_Category, Year, Month_Num,
            Current_Month_Sales, Previous_Month_Sales,
            case
                when Previous_Month_Sales = 0 then null
                else (Current_Month_Sales - Previous_Month_Sales) * 100.0 / Previous_Month_Sales
            end as MoM_Growth_Percentage
        from LaggedSales
        order by Product_Category, Year, Month_Num;
    """,

    "Q10: Weekend vs Weekday by Age": """
        select
            Age_Group,
            case when Is_Weekend = 1 then 'Weekend' else 'Weekday' end as Day_Type,
            sum(Purchase_Amount) as Total_Sales
        from v_SalesAnalysis
        where Year = 2019
        group by Age_Group, Is_Weekend
        order by Age_Group, Day_Type;
    """,

    "Q12: Store Growth (Quarterly 2017)": """
        with QuarterlySales as (
            select
                Store_Name, Quarter,
                sum(Purchase_Amount) as Current_Quarter_Sales
            from v_SalesAnalysis
            where Year = 2017
            group by Store_Name, Quarter
        ),
        LaggedQuarterlySales as (
            select
                Store_Name, Quarter, Current_Quarter_Sales,
                lag(Current_Quarter_Sales, 1, 0) over(
                    partition by Store_Name
                    order by Quarter
                ) as Previous_Quarter_Sales
            from QuarterlySales
        )
        select
            Store_Name, Quarter, Current_Quarter_Sales, Previous_Quarter_Sales,
            case
                when Previous_Quarter_Sales = 0 then null
                else (Current_Quarter_Sales - Previous_Quarter_Sales) * 100.0 / Previous_Quarter_Sales
            end as QoQ_Growth_Percentage
        from LaggedQuarterlySales
        order by Store_Name, Quarter;
    """,

    "Q13: Supplier Sales by Store/Product": """
        select
            Store_Name, Supplier_Name, Product_ID, Product_Category,
            sum(Purchase_Amount) as Total_Sales
        from v_SalesAnalysis
        group by Store_Name, Supplier_Name, Product_ID, Product_Category
        order by Store_Name, Supplier_Name, Total_Sales desc;
    """,

    "Q14: Seasonal Product Sales": """
        select
            Product_ID,
            case 
                when Month_Num in (3, 4, 5) then 'Spring'
                when Month_Num in (6, 7, 8) then 'Summer'
                when Month_Num in (9, 10, 11) then 'Fall'
                else 'Winter'
            end as Season,
            sum(Purchase_Amount) as Total_Sales
        from v_SalesAnalysis
        group by Product_ID, Season
        order by Product_ID, Season;
    """,

    "Q15: Monthly Volatility by Store/Supplier": """
        with MonthlySales as (
            select
                Store_Name, Supplier_Name, Year, Month_Num,
                sum(Purchase_Amount) as Current_Month_Sales
            from v_SalesAnalysis
            group by Store_Name, Supplier_Name, Year, Month_Num
        ),
        LaggedSales as (
            select
                Store_Name, Supplier_Name, Year, Month_Num, Current_Month_Sales,
                lag(Current_Month_Sales, 1, 0) over(
                    partition by Store_Name, Supplier_Name
                    order by Year, Month_Num
                ) as Previous_Month_Sales
            from MonthlySales
        )
        select
            Store_Name, Supplier_Name, Year, Month_Num,
            Current_Month_Sales, Previous_Month_Sales,
            case
                when Previous_Month_Sales = 0 then null
                else (Current_Month_Sales - Previous_Month_Sales) * 100.0 / Previous_Month_Sales
            end as MoM_Volatility_Percent
        from LaggedSales
        order by Store_Name, Supplier_Name, Year, Month_Num;
    """,

    "Q16: Top 5 Product Affinity": """
        select
            f1.Product_ID as Product_A,
            f2.Product_ID as Product_B,
            count(*) as Times_Purchased_Together
        from FactSales f1
        join FactSales f2 
            on f1.Transaction_ID = f2.Transaction_ID
            and f1.Product_ID < f2.Product_ID
        group by f1.Product_ID, f2.Product_ID
        order by Times_Purchased_Together desc
        limit 5;
    """,

    "Q17: Yearly Revenue with ROLLUP": """
        select
            Year, Store_Name, Supplier_Name, Product_Category, Product_ID,
            sum(Purchase_Amount) as Total_Revenue
        from v_SalesAnalysis
        group by
            Year, Store_Name, Supplier_Name, Product_Category, Product_ID with rollup
        order by
            Year, Store_Name, Supplier_Name, Product_Category, Product_ID;
    """,

    "Q18: Sales by H1 vs H2": """
        select
            Year, Product_ID,
            sum(case when Quarter in (1, 2) then Purchase_Amount else 0 end) as H1_Revenue,
            sum(case when Quarter in (3, 4) then Purchase_Amount else 0 end) as H2_Revenue,
            sum(case when Quarter in (1, 2) then Quantity else 0 end) as H1_Volume,
            sum(case when Quarter in (3, 4) then Quantity else 0 end) as H2_Volume,
            sum(Purchase_Amount) as Total_Yearly_Revenue,
            sum(Quantity) as Total_Yearly_Volume
        from v_SalesAnalysis
        group by Year, Product_ID
        order by Year, Total_Yearly_Revenue desc;
    """,

    "Q19: Identify Revenue Spikes": """
        with DailyProductSales as (
            select
                Product_ID, Full_Date,
                sum(Purchase_Amount) as Daily_Sales
            from v_SalesAnalysis
            group by Product_ID, Full_Date
        ),
        ProductAverages as (
            select
                Product_ID, Full_Date, Daily_Sales,
                avg(Daily_Sales) over(partition by Product_ID) as Avg_Daily_Sales
            from DailyProductSales
        )
        select Product_ID, Full_Date, Daily_Sales, Avg_Daily_Sales
        from ProductAverages
        where Daily_Sales > (Avg_Daily_Sales * 2)
        order by Product_ID, Full_Date;
    """,

    "Q20: CREATE VIEW (Store Sales)": """
        create or replace view v_Store_Quarterly_Sales as
        select
            Store_Name, Year, Quarter,
            sum(Purchase_Amount) as Total_Quarterly_Sales
        from v_SalesAnalysis
        group by Store_Name, Year, Quarter
        order by Store_Name, Year, Quarter;
    """,
    
    "Q_VIEW: Run v_Store_Quarterly_Sales": """
        select * from v_Store_Quarterly_Sales;
    """,
    
    "Q_VIEW: CREATE v_SalesAnalysis": """
        create or replace view v_SalesAnalysis as
        select
            f.Transaction_ID, f.Quantity, f.Price, f.Purchase_Amount,
            d.Full_Date, d.Day_Of_Week_Name, d.Is_Weekend, 
            d.Month_Name, d.Month_Num, d.Quarter, d.Year,
            c.Customer_ID, c.Age_Group, c.Gender, c.Occupation, 
            c.City_Category, c.Stay_In_Current_City_Years, c.Marital_Status,
            p.Product_ID, p.Product_Category, 
            s.Store_ID, s.Store_Name,
            sp.Supplier_ID, sp.Supplier_Name
        from FactSales f
        join DimDate d on f.Date_Key = d.Date_Key
        join DimCustomer c on f.Customer_ID = c.Customer_ID
        join DimProduct p on f.Product_ID = p.Product_ID
        join DimStore s on f.Store_ID = s.Store_ID
        join DimSupplier sp on f.Supplier_ID = sp.Supplier_ID;
    """
}