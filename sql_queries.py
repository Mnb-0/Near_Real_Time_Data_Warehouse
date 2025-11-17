QUERIES = {
    "q1/q11: top 5 products": """
        with rankedproducts as (
            select
                v.year, v.month_name,
                case when v.is_weekend = 1 then 'weekend' else 'weekday' end as day_type,
                v.product_id, sum(v.purchase_amount) as total_revenue,
                row_number() over(
                    partition by v.year, v.month_num, v.is_weekend 
                    order by sum(v.purchase_amount) desc
                ) as ranknum
            from v_salesanalysis v
            where v.year = 2019
            group by v.year, v.month_name, v.month_num, v.is_weekend, v.product_id
        )
        select year, month_name, day_type, product_id, total_revenue, ranknum
        from rankedproducts
        where ranknum <= 5
        order by year, month_name, day_type, ranknum;
    """,

    "q2: demographics by city": """
        select
            city_category, gender, age_group,
            sum(purchase_amount) as total_purchase_amount,
            count(distinct customer_id) as total_customers
        from v_salesanalysis
        group by city_category, gender, age_group
        order by city_category, total_purchase_amount desc;
    """,

    "q3: category sales by occupation": """
        select
            occupation, product_category,
            sum(purchase_amount) as total_sales
        from v_salesanalysis
        group by occupation, product_category
        order by occupation, total_sales desc;
    """,

    "q4: quarterly trend by demo": """
        select
            quarter, gender, age_group,
            sum(purchase_amount) as total_purchases
        from v_salesanalysis
        where year = 2019
        group by quarter, gender, age_group
        order by quarter, gender, age_group;
    """,

    "q5: top 5 occupations by category": """
        with rankedoccupations as (
            select
                product_category, occupation,
                sum(purchase_amount) as total_sales,
                row_number() over(
                    partition by product_category 
                    order by sum(purchase_amount) desc
                ) as ranknum
            from v_salesanalysis
            group by product_category, occupation
        )
        select product_category, occupation, total_sales
        from rankedoccupations
        where ranknum <= 5
        order by product_category, ranknum;
    """,

    "q6: city perf by marital (6-mo)": """
        select
            year, month_name, city_category,
            case when marital_status = 1 then 'married' else 'single' end as marital_status,
            sum(purchase_amount) as total_purchases
        from v_salesanalysis
        where full_date between '2019-01-01' and '2019-06-30'
        group by year, month_num, month_name, city_category, marital_status
        order by year, month_num, city_category;
    """,

    "q7: avg purchase by stay/gender": """
        select
            stay_in_current_city_years, gender,
            avg(purchase_amount) as average_purchase_amount
        from v_salesanalysis
        group by stay_in_current_city_years, gender
        order by stay_in_current_city_years, gender;
    """,

    "q8: top 5 cities by category": """
        with rankedcities as (
            select
                product_category, city_category,
                sum(purchase_amount) as total_revenue,
                row_number() over(
                    partition by product_category
                    order by sum(purchase_amount) desc
                ) as ranknum
            from v_salesanalysis
            group by product_category, city_category
        )
        select product_category, city_category, total_revenue
        from rankedcities
        where ranknum <= 5
        order by product_category, ranknum;
    """,

    "q9: monthly growth by category": """
        with monthlysales as (
            select
                product_category, year, month_num,
                sum(purchase_amount) as current_month_sales
            from v_salesanalysis
            where year = 2019
            group by product_category, year, month_num
        ),
        laggedsales as (
            select
                product_category, year, month_num, current_month_sales,
                lag(current_month_sales, 1, 0) over(
                    partition by product_category
                    order by year, month_num
                ) as previous_month_sales
            from monthlysales
        )
        select
            product_category, year, month_num,
            current_month_sales, previous_month_sales,
            case
                when previous_month_sales = 0 then null
                else (current_month_sales - previous_month_sales) * 100.0 / previous_month_sales
            end as mom_growth_percentage
        from laggedsales
        order by product_category, year, month_num;
    """,

    "q10: weekend vs weekday by age": """
        select
            age_group,
            case when is_weekend = 1 then 'weekend' else 'weekday' end as day_type,
            sum(purchase_amount) as total_sales
        from v_salesanalysis
        where year = 2019
        group by age_group, is_weekend
        order by age_group, day_type;
    """,

    "q12: store growth (quarterly 2017)": """
        with quarterlysales as (
            select
                store_name, quarter,
                sum(purchase_amount) as current_quarter_sales
            from v_salesanalysis
            where year = 2017
            group by store_name, quarter
        ),
        laggedquarterlysales as (
            select
                store_name, quarter, current_quarter_sales,
                lag(current_quarter_sales, 1, 0) over(
                    partition by store_name
                    order by quarter
                ) as previous_quarter_sales
            from quarterlysales
        )
        select
            store_name, quarter, current_quarter_sales, previous_quarter_sales,
            case
                when previous_quarter_sales = 0 then null
                else (current_quarter_sales - previous_quarter_sales) * 100.0 / previous_quarter_sales
            end as qoq_growth_percentage
        from laggedquarterlysales
        order by store_name, quarter;
    """,

    "q13: supplier sales by store/product": """
        select
            store_name, supplier_name, product_id, product_category,
            sum(purchase_amount) as total_sales
        from v_salesanalysis
        group by store_name, supplier_name, product_id, product_category
        order by store_name, supplier_name, total_sales desc;
    """,

    "q14: seasonal product sales": """
        select
            product_id,
            case 
                when month_num in (3, 4, 5) then 'spring'
                when month_num in (6, 7, 8) then 'summer'
                when month_num in (9, 10, 11) then 'fall'
                else 'winter'
            end as season,
            sum(purchase_amount) as total_sales
        from v_salesanalysis
        group by product_id, season
        order by product_id, season;
    """,

    "q15: monthly volatility by store/supplier": """
        with monthlysales as (
            select
                store_name, supplier_name, year, month_num,
                sum(purchase_amount) as current_month_sales
            from v_salesanalysis
            group by store_name, supplier_name, year, month_num
        ),
        laggedsales as (
            select
                store_name, supplier_name, year, month_num, current_month_sales,
                lag(current_month_sales, 1, 0) over(
                    partition by store_name, supplier_name
                    order by year, month_num
                ) as previous_month_sales
            from monthlysales
        )
        select
            store_name, supplier_name, year, month_num,
            current_month_sales, previous_month_sales,
            case
                when previous_month_sales = 0 then null
                else (current_month_sales - previous_month_sales) * 100.0 / previous_month_sales
            end as mom_volatility_percent
        from laggedsales
        order by store_name, supplier_name, year, month_num;
    """,

    "q16: top 5 product affinity": """
        select
            f1.product_id as product_a,
            f2.product_id as product_b,
            count(*) as times_purchased_together
        from factsales f1
        join factsales f2 
            on f1.transaction_id = f2.transaction_id
            and f1.product_id < f2.product_id
        group by f1.product_id, f2.product_id
        order by times_purchased_together desc
        limit 5;
    """,

    "q17: yearly revenue with rollup": """
        select
            year, store_name, supplier_name, product_category, product_id,
            sum(purchase_amount) as total_revenue
        from v_salesanalysis
        group by
            year, store_name, supplier_name, product_category, product_id with rollup
        order by
            year, store_name, supplier_name, product_category, product_id;
    """,

    "q18: sales by h1 vs h2": """
        select
            year, product_id,
            sum(case when quarter in (1, 2) then purchase_amount else 0 end) as h1_revenue,
            sum(case when quarter in (3, 4) then purchase_amount else 0 end) as h2_revenue,
            sum(case when quarter in (1, 2) then quantity else 0 end) as h1_volume,
            sum(case when quarter in (3, 4) then quantity else 0 end) as h2_volume,
            sum(purchase_amount) as total_yearly_revenue,
            sum(quantity) as total_yearly_volume
        from v_salesanalysis
        group by year, product_id
        order by year, total_yearly_revenue desc;
    """,

    "q19: identify revenue spikes": """
        with dailyproductsales as (
            select
                product_id, full_date,
                sum(purchase_amount) as daily_sales
            from v_salesanalysis
            group by product_id, full_date
        ),
        productaverages as (
            select
                product_id, full_date, daily_sales,
                avg(daily_sales) over(partition by product_id) as avg_daily_sales
            from dailyproductsales
        )
        select product_id, full_date, daily_sales, avg_daily_sales
        from productaverages
        where daily_sales > (avg_daily_sales * 2)
        order by product_id, full_date;
    """,

    "q20: create view (store sales)": """
        create or replace view v_store_quarterly_sales as
        select
            store_name, year, quarter,
            sum(purchase_amount) as total_quarterly_sales
        from v_salesanalysis
        group by store_name, year, quarter
        order by store_name, year, quarter;
    """,

    "q_view: run v_store_quarterly_sales": """
        select * from v_store_quarterly_sales;
    """,

    "q_view: create v_salesanalysis": """
        create or replace view v_salesanalysis as
        select
            f.transaction_id, f.quantity, f.price, f.purchase_amount,
            d.full_date, d.day_of_week_name, d.is_weekend, 
            d.month_name, d.month_num, d.quarter, d.year,
            c.customer_id, c.age_group, c.gender, c.occupation, 
            c.city_category, c.stay_in_current_city_years, c.marital_status,
            p.product_id, p.product_category, 
            s.store_id, s.store_name,
            sp.supplier_id, sp.supplier_name
        from factsales f
        join dimdate d on f.date_key = d.date_key
        join dimcustomer c on f.customer_id = c.customer_id
        join dimproduct p on f.product_id = p.product_id
        join dimstore s on f.store_id = s.store_id
        join dimsupplier sp on f.supplier_id = sp.supplier_id;
    """
}
