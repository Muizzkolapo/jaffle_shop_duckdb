

with source as (

    select * from {{ source('main', 'customers') }}   --Changed from raw_customers

),

renamed as (

    select
        id,
        first_name,
        last_name

    from source

)

select * from renamed

