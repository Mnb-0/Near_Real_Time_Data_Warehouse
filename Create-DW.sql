drop database if exists walmart;
create database if not exists walmart;
use walmart;

set foreign_key_checks=0;

drop table if exists dimdate;
create table dimdate (
    date_key          int primary key,
    full_date         date not null,
    day_of_week_name  varchar(10) not null,
    day_of_week_num   int not null,
    is_weekend        tinyint(1) not null,
    month_name        varchar(10) not null,
    month_num         int not null,
    quarter           int not null,
    year              int not null,
    index idx_dimdate_full_date (full_date)
) engine=innodb;

drop table if exists dimcustomer;
create table dimcustomer (
    customer_id                 int primary key,
    age_group                   varchar(10) not null,
    gender                      char(1) not null,
    occupation                  varchar(50) not null,
    city_category               char(1) not null,
    stay_in_current_city_years  varchar(5) not null,
    marital_status              int not null,
    index idx_dimcustomer_city_cat (city_category),
    index idx_dimcustomer_occupation (occupation)
) engine=innodb;

drop table if exists dimproduct;
create table dimproduct (
    product_id          varchar(20) primary key,
    product_category    varchar(50) not null,
    index idx_dimproduct_cat1 (product_category)
) engine=innodb;

drop table if exists factsales;
create table factsales (
    transaction_id      varchar(50) not null,
    customer_id         int not null,
    product_id          varchar(20) not null,
    date_key            int not null,
    purchase_amount     decimal(12,2) not null,
    primary key (transaction_id, product_id),
    constraint fk_customer
        foreign key(customer_id) references dimcustomer(customer_id),
    constraint fk_product
        foreign key(product_id) references dimproduct(product_id),
    constraint fk_date
        foreign key(date_key) references dimdate(date_key),
    index idx_factsales_date_key (date_key),
    index idx_factsales_cust_prod (customer_id, product_id)
) engine=innodb;

set foreign_key_checks=1;

select * from dimproduct;
select * from dimdate;
select * from dimcustomer;
select * from factsales;
select count(*) from factsales;
