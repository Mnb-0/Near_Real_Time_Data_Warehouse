use walmart;

create or replace view v_salesanalysis as
select
    f.transaction_id,
    f.purchase_amount,
    d.full_date,
    d.day_of_week_name,
    d.is_weekend,
    d.month_name,
    d.month_num,
    d.quarter,
    d.year,
    c.customer_id,
    c.age_group,
    c.gender,
    c.occupation,
    c.city_category,
    c.stay_in_current_city_years,
    c.marital_status,
    p.product_id,
    p.product_category
from
    factsales f
join
    dimdate d on f.date_key = d.date_key
join
    dimcustomer c on f.customer_id = c.customer_id
join
    dimproduct p on f.product_id = p.product_id;

-- Q1, Q11
with rankedproducts as (
    select
        v.year,
        v.month_name,
        case when v.is_weekend = 1 then 'Weekend' else 'Weekday' end as day_type,
        v.product_id,
        sum(v.purchase_amount) as total_revenue,
        row_number() over(
            partition by v.year, v.month_num, v.is_weekend
            order by sum(v.purchase_amount) desc
        ) as ranknum
    from
        v_salesanalysis v
    where
        v.year = 2019
    group by
        v.year, v.month_name, v.month_num, v.is_weekend, v.product_id
)
select
    year, month_name, day_type, product_id, total_revenue, ranknum
from
    rankedproducts
where
    ranknum <= 5
order by
    year, month_name, day_type, ranknum;

-- Q2
select
    city_category,
    gender,
    age_group,
    sum(purchase_amount) as total_purchase_amount,
    count(distinct customer_id) as total_customers
from
    v_salesanalysis
group by
    city_category, gender, age_group
order by
    city_category, total_purchase_amount desc;

-- Q3
select
    occupation,
    product_category_1,
    sum(purchase_amount) as total_sales
from
    v_salesanalysis
group by
    occupation, product_category_1
order by
    occupation, total_sales desc;

-- Q4
select
    quarter,
    gender,
    age_group,
    sum(purchase_amount) as total_purchases
from
    v_salesanalysis
where
    year = 2019
group by
    quarter, gender, age_group
order by
    quarter, gender, age_group;

-- Q5
with rankedoccupations as (
    select
        product_category_1,
        occupation,
        sum(purchase_amount) as total_sales,
        row_number() over(
            partition by product_category_1
            order by sum(purchase_amount) desc
        ) as ranknum
    from
        v_salesanalysis
    group by
        product_category_1, occupation
)
select
    product_category_1, occupation, total_sales
from
    rankedoccupations
where
    ranknum <= 5
order by
    product_category_1, ranknum;

-- Q6
select
    year,
    month_name,
    city_category,
    case when marital_status = 1 then 'Married' else 'Single' end as marital_status,
    sum(purchase_amount) as total_purchases
from
    v_salesanalysis
where
    full_date between '2019-01-01' and '2019-06-30'
group by
    year, month_num, month_name, city_category, marital_status
order by
    year, month_num, city_category;

-- Q7
select
    stay_in_current_city_years,
    gender,
    avg(purchase_amount) as average_purchase_amount
from
    v_salesanalysis
group by
    stay_in_current_city_years, gender
order by
    stay_in_current_city_years, gender;

-- Q8
with rankedcities as (
    select
        product_category_1,
        city_category,
        sum(purchase_amount) as total_revenue,
        row_number() over(
            partition by product_category_1
            order by sum(purchase_amount) desc
        ) as ranknum
    from
        v_salesanalysis
    group by
        product_category_1, city_category
)
select
    product_category_1, city_category, total_revenue
from
    rankedcities
where
    ranknum <= 5
order by
    product_category_1, ranknum;

-- Q9
with monthlysales as (
    select
        product_category_1,
        year,
        month_num,
        sum(purchase_amount) as current_month_sales
    from
        v_salesanalysis
    where
        year = 2019
    group by
        product_category_1, year, month_num
),
laggedsales as (
    select
        product_category_1,
        year,
        month_num,
        current_month_sales,
        lag(current_month_sales, 1, 0) over(
            partition by product_category_1
            order by year, month_num
        ) as previous_month_sales
    from
        monthlysales
)
select
    product_category_1,
    year,
    month_num,
    current_month_sales,
    previous_month_sales,
    case
        when previous_month_sales = 0 then null
        else (current_month_sales - previous_month_sales) * 100.0 / previous_month_sales
    end as mom_growth_percentage
from
    laggedsales
order by
    product_category_1, year, month_num;

-- Q10
select
    age_group,
    case when is_weekend = 1 then 'Weekend' else 'Weekday' end as day_type,
    sum(purchase_amount) as total_sales
from
    v_salesanalysis
where
    year = 2019
group by
    age_group, is_weekend
order by
    age_group, day_type;

-- Q12
with quarterlysales as (
    select
        city_category,
        quarter,
        sum(purchase_amount) as current_quarter_sales
    from
        v_salesanalysis
    where
        year = 2019
    group by
        city_category, quarter
),
laggedquarterlysales as (
    select
        city_category,
        quarter,
        current_quarter_sales,
        lag(current_quarter_sales, 1, 0) over(
            partition by city_category
            order by quarter
        ) as previous_quarter_sales
    from
        quarterlysales
)
select
    city_category,
    quarter,
    current_quarter_sales,
    previous_quarter_sales,
    case
        when previous_quarter_sales = 0 then null
        else (current_quarter_sales - previous_quarter_sales) * 100.0 / previous_quarter_sales
    end as qoq_growth_percentage
from
    laggedquarterlysales
order by
    city_category, quarter;

-- Q13
select
    city_category,
    product_id,
    product_category_1,
    sum(purchase_amount) as total_sales
from
    v_salesanalysis
group by
    city_category, product_id, product_category_1
order by
    city_category, product_id;

-- Q14
select
    product_id,
    case
        when month_num in (3,4,5) then 'Spring'
        when month_num in (6,7,8) then 'Summer'
        when month_num in (9,10,11) then 'Fall'
        else 'Winter'
    end as season,
    sum(purchase_amount) as total_sales
from
    v_salesanalysis
group by
    product_id, season
order by
    product_id, season;

-- Q15
with monthlysales as (
    select
        city_category,
        product_category_1,
        year,
        month_num,
        sum(purchase_amount) as current_month_sales
    from
        v_salesanalysis
    group by
        city_category, product_category_1, year, month_num
),
laggedsales as (
    select
        city_category,
        product_category_1,
        year,
        month_num,
        current_month_sales,
        lag(current_month_sales, 1, 0) over(
            partition by city_category, product_category_1
            order by year, month_num
        ) as previous_month_sales
    from
        monthlysales
)
select
    city_category,
    product_category_1,
    year,
    month_num,
    current_month_sales,
    previous_month_sales,
    case
        when previous_month_sales = 0 then null
        else (current_month_sales - previous_month_sales) * 100.0 / previous_month_sales
    end as mom_volatility_percent
from
    laggedsales
order by
    city_category, product_category_1, year, month_num;

-- Q16
select
    f1.product_id as product_a,
    f2.product_id as product_b,
    count(*) as times_purchased_together
from
    factsales f1
join
    factsales f2
    on f1.transaction_id = f2.transaction_id
    and f1.product_id < f2.product_id
group by
    f1.product_id, f2.product_id
order by
    times_purchased_together desc
limit 5;

-- Q17
select
    year,
    city_category,
    product_category_1,
    product_id,
    sum(purchase_amount) as total_revenue
from
    v_salesanalysis
group by
    year, city_category, product_category_1, product_id with rollup
order by
    year, city_category, product_category_1, product_id;

-- Q18
select
    year,
    product_id,
    sum(case when quarter in (1,2) then purchase_amount else 0 end) as h1_revenue,
    sum(case when quarter in (3,4) then purchase_amount else 0 end) as h2_revenue,
    count(case when quarter in (1,2) then transaction_id else null end) as h1_volume,
    count(case when quarter in (3,4) then transaction_id else null end) as h2_volume,
    sum(purchase_amount) as total_yearly_revenue,
    count(transaction_id) as total_yearly_volume
from
    v_salesanalysis
group by
    year, product_id
order by
    year, total_yearly_revenue desc;

-- Q19
with dailyproductsales as (
    select
        product_id,
        full_date,
        sum(purchase_amount) as daily_sales
    from
        v_salesanalysis
    group by
        product_id, full_date
),
productaverages as (
    select
        product_id,
        full_date,
        daily_sales,
        avg(daily_sales) over(partition by product_id) as avg_daily_sales
    from
        dailyproductsales
)
select
    product_id,
    full_date,
    daily_sales,
    avg_daily_sales
from
    productaverages
where
    daily_sales > (avg_daily_sales * 2)
order by
    product_id, full_date;

-- Q20
create or replace view v_city_quarterly_sales as
select
    city_category,
    year,
    quarter,
    sum(purchase_amount) as total_quarterly_sales
from
    v_salesanalysis
group by
    city_category, year, quarter
order by
    city_category, year, quarter;