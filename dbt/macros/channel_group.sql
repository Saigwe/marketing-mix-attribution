{#-
  Default channel grouping, simplified from GA4's rules for the sources in this sample.
  - The store referring to itself (shop.googlemerchandisestore.com) is a self-referral, counted as Direct, as GA4's
    unwanted-referral exclusion would.
  - Google obfuscates part of the sample ('<Other>', '(data deleted)'); those sessions are Unknown, not guessed.
-#}
{% macro channel_group(source, medium) %}
case
    when {{ source }} is null or {{ medium }} is null then 'Unknown'
    when {{ source }} in ('<Other>', '(data deleted)') or {{ medium }} in ('<Other>', '(data deleted)') then 'Unknown'
    when {{ source }} = '(direct)' and {{ medium }} in ('(none)', '(not set)') then 'Direct'
    when {{ medium }} = 'referral' and {{ source }} like '%googlemerchandisestore.com' then 'Direct'
    when {{ medium }} = 'organic' then 'Organic Search'
    when {{ medium }} in ('cpc', 'ppc', 'paidsearch') then 'Paid Search'
    when {{ medium }} = 'affiliate' then 'Affiliates'
    when {{ medium }} = 'email' then 'Email'
    when {{ medium }} = 'referral' then 'Referral'
    else 'Other'
end
{% endmacro %}
