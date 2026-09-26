
## absolute_volume.log  (orig 32 lines, blind 32 lines)
  = 
  = === (a) platform-level totals: pre/post average monthly volume, by language ===
  =   python       pre= 19204.0/mo  post_avg=  4616.5/mo (-76.0%)  last12avg=   551.3/mo (-97.1%)
  =   javascript   pre= 13191.8/mo  post_avg=  2817.1/mo (-78.6%)  last12avg=   231.4/mo (-98.2%)
  =   java         pre=  6126.8/mo  post_avg=  1628.6/mo (-73.4%)  last12avg=   236.4/mo (-96.1%)
  = 
  = === (b) absolute volume by substitutability bin: N_t x p_hat_s,t ===
  = 
  =   -- python --
  O     s1: pre_abs=  2904.5/mo  post_abs=  1057.4/mo  Δ=-63.6%
  B     s1: pre_abs=  4440.2/mo  post_abs=  1394.5/mo  Δ=-68.6%
  O     s2: pre_abs=  4216.9/mo  post_abs=  1217.1/mo  Δ=-71.1%
  B     s2: pre_abs=  3149.2/mo  post_abs=   821.0/mo  Δ=-73.9%
  O     s3: pre_abs=  7045.5/mo  post_abs=  1638.3/mo  Δ=-76.7%
  B     s3: pre_abs=  6238.6/mo  post_abs=  1378.1/mo  Δ=-77.9%
  O     s4: pre_abs=  4945.0/mo  post_abs=   692.3/mo  Δ=-86.0%
  B     s4: pre_abs=  4326.3/mo  post_abs=   670.8/mo  Δ=-84.5%
  O     [sanity] mean (sum of Nhat_s1..s4) / platform_total = 0.996 (expect ~ (100-s0)/100)
  B     [sanity] mean (sum of Nhat_s1..s4) / platform_total = 0.917 (expect ~ (100-s0)/100)
  = 
  =   -- javascript --
  =     s1: pre_abs=  2166.3/mo  post_abs=   544.6/mo  Δ=-74.9%
  =     s2: pre_abs=  3099.9/mo  post_abs=   765.6/mo  Δ=-75.3%
  =     s3: pre_abs=  5328.1/mo  post_abs=  1006.0/mo  Δ=-81.1%
  =     s4: pre_abs=  2567.2/mo  post_abs=   494.5/mo  Δ=-80.7%
  =     [sanity] mean (sum of Nhat_s1..s4) / platform_total = 0.995 (expect ~ (100-s0)/100)
  = 
  =   -- java --
  =     s1: pre_abs=  1536.5/mo  post_abs=   476.1/mo  Δ=-69.0%
  =     s2: pre_abs=  1492.4/mo  post_abs=   423.8/mo  Δ=-71.6%
  =     s3: pre_abs=  2018.6/mo  post_abs=   494.3/mo  Δ=-75.5%
  =     s4: pre_abs=  1052.9/mo  post_abs=   223.7/mo  Δ=-78.7%
  =     [sanity] mean (sum of Nhat_s1..s4) / platform_total = 0.993 (expect ~ (100-s0)/100)
  = 
  O written: E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\orig\02_estimation\absolute_volume.json
  B written: E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\blind\02_estimation\absolute_volume.json
  = per-language monthly reconstructed series: absolute_volume_series_{python,javascript,java}.csv
  = 

## answer_side_test.log  (orig 17 lines, blind 17 lines)
  O N = 5,975 python questions, 60 months
  B N = 5,500 python questions, 60 months
  = 
  = === 描述:各档 回答率 / 平均回答数 (pre vs post) ===
  O   s1: is_answered 0.438 -> 0.375   answer_count 0.90 -> 0.80
  B   s1: is_answered 0.564 -> 0.485   answer_count 1.08 -> 0.99
  O   s2: is_answered 0.530 -> 0.527   answer_count 1.03 -> 0.95
  B   s2: is_answered 0.556 -> 0.554   answer_count 1.12 -> 1.08
  O   s3: is_answered 0.631 -> 0.661   answer_count 1.28 -> 1.33
  B   s3: is_answered 0.599 -> 0.639   answer_count 1.24 -> 1.31
  O   s4: is_answered 0.738 -> 0.761   answer_count 1.61 -> 1.86
  B   s4: is_answered 0.741 -> 0.776   answer_count 1.62 -> 1.69
  = 
  = === 回答端剂量反应 DiD(月 FE 吸收答案累积差;按月聚类) ===
  O   回答率   : score×post = +0.0320 (SE 0.0140, p=0.022)
  B   回答率   : score×post = +0.0417 (SE 0.0128, p=0.001)
  O   回答数   : score×post = +0.1088 (SE 0.0558, p=0.051)
  B   回答数   : score×post = +0.0505 (SE 0.0284, p=0.075)
  O   二元(VER×post,回答率): -0.0524 (SE 0.0301, p=0.082)
  B   二元(VER×post,回答率): -0.0761 (SE 0.0322, p=0.018)
  = 
  O === 稳健性:剔除最后6个月 (N=5,380) ===
  B === 稳健性:剔除最后6个月 (N=4,968) ===
  O   s1: is_answered 0.438 -> 0.366
  B   s1: is_answered 0.564 -> 0.471
  O   s4: is_answered 0.738 -> 0.748
  B   s4: is_answered 0.741 -> 0.778
  = 

## asker_cohort_prelim.log  (orig 55 lines, blind 55 lines)
  = merged N=6000  months 2021-06..2026-05  pre=1800 post=4200
  = 
  = === (a) owner resolution ===
  =   resolved 5877/6000 = 98.0%
  O   by bin:    {0: 1.0, 1: 0.9759, 2: 0.9792, 3: 0.9811, 4: 0.9807}   chi2 p=0.7865
  B   by bin:    {0: 0.968, 1: 0.9794, 2: 0.9785, 3: 0.9845, 4: 0.9777}   chi2 p=0.2251
  =   by period: {0: 0.9778, 1: 0.9802}   chi2 p=0.6052
  = 
  = === (b) did the asker pool shift? ===
  =   threshold T = max pre-period user_id = 20385089
  =   share of questions from pre-ChatGPT-registered accounts:
  =     pre  100.0%   (100% by construction)
  =     post 60.9%  -> 39.1% of post questions come from NEW accounts
  =   median user_id: pre 15,638,402 -> post 16,937,219  (higher = registered later)
  =   Mann-Whitney p = 8.98e-27
  = 
  = === (c) registration recency vs substitutability ===
  O   Spearman rho(user_id, s) = -0.0945, p = 3.93e-13
  B   Spearman rho(user_id, s) = -0.1243, p = 1.17e-21
  =   mean s by whether the account is new (post-period questions only):
  O     pre-registered accounts : 2.416  (N=2508)
  B     pre-registered accounts : 2.124  (N=2508)
  O     new accounts            : 2.272  (N=1609)
  B     new accounts            : 1.878  (N=1609)
  = 
  = === (d) shift-share decomposition of the fall in mean s ===
  =   cohort cuts (pre-period id terciles): 12,723,659 / 17,047,912 / T=20,385,089
  =   shares  pre : {'cohort_old': 0.3335, 'cohort_mid': 0.333, 'cohort_recent': 0.3335, 'new': 0.0}
  =   shares  post: {'cohort_old': 0.3804, 'cohort_mid': 0.121, 'cohort_recent': 0.1078, 'new': 0.3908}
  O   mean s  pre : {'cohort_old': 2.78, 'cohort_mid': 2.672, 'cohort_recent': 2.721, 'new': nan}
  B   mean s  pre : {'cohort_old': 2.566, 'cohort_mid': 2.35, 'cohort_recent': 2.387, 'new': nan}
  O   mean s  post: {'cohort_old': 2.469, 'cohort_mid': 2.331, 'cohort_recent': 2.322, 'new': 2.272}
  B   mean s  post: {'cohort_old': 2.185, 'cohort_mid': 2.012, 'cohort_recent': 2.032, 'new': 1.878}
  O   TOTAL change in mean s                     : -0.3649
  B   TOTAL change in mean s                     : -0.4066
  O   WITHIN  (same cohort asks less substitutable): -0.2763  ( 75.7%)
  B   WITHIN  (same cohort asks less substitutable): -0.2908  ( 71.5%)
  O   BETWEEN (the cohort mix changed = the rival) : -0.0886  ( 24.3%)
  B   BETWEEN (the cohort mix changed = the rival) : -0.1158  ( 28.5%)
  = 
  = === (e) dose-response (paper's spec) on subsamples ===
  O   all askers (truncated panel)       N= 5852  zeros= 0.0%
  B   all askers (truncated panel)       N= 5393  zeros= 0.0%
  O       log-OLS gamma=-0.4163 (SE 0.0680) p=9.21e-10   s4/s1=-71.3%
  B       log-OLS gamma=-0.3016 (SE 0.0390) p=1.07e-14   s4/s1=-59.5%
  O       PPML    gamma=-0.3685 (SE 0.0594) p=5.57e-10
  B       PPML    gamma=-0.2845 (SE 0.0385) p=1.38e-13
  O   pre-ChatGPT-registered accounts ONLY N= 4258  zeros= 0.0%
  B   pre-ChatGPT-registered accounts ONLY N= 3970  zeros= 0.0%
  O       log-OLS gamma=-0.3672 (SE 0.0680) p=6.6e-08   s4/s1=-66.8%
  B       log-OLS gamma=-0.2547 (SE 0.0444) p=9.66e-09   s4/s1=-53.4%
  O       PPML    gamma=-0.3185 (SE 0.0589) p=6.45e-08
  B       PPML    gamma=-0.2249 (SE 0.0421) p=9.18e-08
  O     of which cohort_old              N= 2146  zeros= 0.4%
  B     of which cohort_old              N= 1992  zeros= 0.0%
  O       log-OLS gamma=-0.3796 (SE 0.0902) p=2.56e-05   s4/s1=-68.0%
  B       log-OLS gamma=-0.2793 (SE 0.0607) p=4.22e-06   s4/s1=-56.7%
  O       PPML    gamma=-0.3357 (SE 0.0770) p=1.32e-05
  B       PPML    gamma=-0.2617 (SE 0.0595) p=1.09e-05
  O     of which cohort_mid              N= 1081  zeros= 5.8%
  B     of which cohort_mid              N= 1005  zeros= 8.3%
  O       log-OLS gamma=-0.2489 (SE 0.0872) p=0.00431   s4/s1=-52.6%
  B       log-OLS gamma=-0.2010 (SE 0.0853) p=0.0185   s4/s1=-45.3%
  O       PPML    gamma=-0.3455 (SE 0.0834) p=3.4e-05
  B       PPML    gamma=-0.2603 (SE 0.0645) p=5.4e-05
  O     of which cohort_recent           N= 1031  zeros=12.5%
  B     of which cohort_recent           N=  973  zeros=12.5%
  O       log-OLS gamma=-0.4174 (SE 0.0976) p=1.89e-05   s4/s1=-71.4%
  B       log-OLS gamma=-0.1970 (SE 0.0656) p=0.00268   s4/s1=-44.6%
  O       PPML    gamma=-0.4051 (SE 0.0991) p=4.38e-05
  B       PPML    gamma=-0.3117 (SE 0.0818) p=0.000138
  = 
  = === (e2) pooled PPML with cohort-x-month FE (absorbs the rival's shock) ===
  O   cells=720, zero cells=8.2%
  B   cells=720, zero cells=8.9%
  O   PPML gamma, cohort-x-month FE = -0.3570 (SE 0.0627), p = 1.25e-08
  B   PPML gamma, cohort-x-month FE = -0.2747 (SE 0.0451), p = 1.15e-09
  O   PPML gamma, plain month FE (same cells) = -0.3185 (SE 0.0529), p = 1.77e-09
  B   PPML gamma, plain month FE (same cells) = -0.2249 (SE 0.0378), p = 2.74e-09
  = 
  O written: E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\orig\02_estimation\asker_cohort_prelim.json
  B written: E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\blind\02_estimation\asker_cohort_prelim.json
  = 

## asker_rival_exact.log  (orig 33 lines, blind 33 lines)
  = === resolution ===
  O   5877/6000 = 98.0%   chi2 by bin p=0.786, by period p=0.605
  B   5877/6000 = 98.0%   chi2 by bin p=0.225, by period p=0.605
  =   usable 5877   pre 1760 / post 4117   months 2021-06..2026-05
  = 
  = === P1: did the novice share fall? ===
  =   accounts <1y old at posting: 53.9% -> 35.5%
  =   median account age: 262d -> 1010d   Mann-Whitney p=1.4e-60   => P1 HOLDS
  = 
  = === P2 (pre-event only): do novices ask more substitutable questions? ===
  O   novice      mean s = 2.680  (N=948)
  B   novice      mean s = 2.345  (N=948)
  O   established mean s = 2.776  (N=812)
  B   established mean s = 2.538  (N=812)
  O   difference = -0.0955  SE 0.0489  95% CI [-0.1913, +0.0003]  p=0.0325
  B   difference = -0.1932  SE 0.0580  95% CI [-0.3068, -0.0796]  p=0.00136
  =   the rival needs this POSITIVE and large => P2 FAILS
  = 
  = === shift-share decomposition of the fall in mean s ===
  O   mean s: novice 2.680->2.290   established 2.776->2.397
  B   mean s: novice 2.345->1.906   established 2.538->2.094
  O   TOTAL   -0.3649
  B   TOTAL   -0.4066
  O   WITHIN  -0.3836  (105.1%)
  B   WITHIN  -0.4417  (108.6%)
  O   BETWEEN +0.0186  ( -5.1%)   <- the rival's share
  B   BETWEEN +0.0351  ( -8.6%)   <- the rival's share
  = 
  = === bounding the rival ===
  O   to carry the whole fall on asker mix, novices would have to score +1.98 higher on a 0-4 scale
  B   to carry the whole fall on asker mix, novices would have to score +2.21 higher on a 0-4 scale
  O   point estimate                         -> between = +0.01757 =  -4.8% of the total
  B   point estimate                         -> between = +0.03556 =  -8.7% of the total
  O   95% CI bound most favourable to it     -> between = -0.00006 =  +0.0% of the total
  B   95% CI bound most favourable to it     -> between = +0.01465 =  -3.6% of the total
  = 
  = === dose-response (PPML, month-clustered) ===
  O   baseline, plain month FE                       gamma=-0.3685 (SE 0.0547)  p=1.64e-11
  B   baseline, plain month FE                       gamma=-0.2845 (SE 0.0354)  p=9.37e-16
  O   novice-by-month FE (absorbs the rival's shock) gamma=-0.3873 (SE 0.0620)  p=4.23e-10
  B   novice-by-month FE (absorbs the rival's shock) gamma=-0.3074 (SE 0.0403)  p=2.33e-14
  O   established askers only                        gamma=-0.4017 (SE 0.0623)  p=1.14e-10
  B   established askers only                        gamma=-0.3147 (SE 0.0452)  p=3.22e-12
  O   novice askers only                             gamma=-0.3721 (SE 0.0672)  p=3.05e-08
  B   novice askers only                             gamma=-0.2997 (SE 0.0500)  p=1.99e-09
  = 
  O written: E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\orig\02_estimation\asker_rival_exact.json
  B written: E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\blind\02_estimation\asker_rival_exact.json
  = 

## asker_rival_test.log  (orig 30 lines, blind 30 lines)
  = symmetric-window sample N=4995  2022-03..2026-05  pre=878 post=4117
  = 
  = === P1: novice share of questions ===
  =   pre 46.8%  ->  post 30.7%   Mann-Whitney p=3.48e-05   => P1 HOLDS
  = 
  = === P2 (pre-event only): do novices ask more substitutable questions? ===
  O   novice mean s      = 2.724  (N=410)
  B   novice mean s      = 2.373  (N=410)
  O   established mean s = 2.752  (N=468)
  B   established mean s = 2.438  (N=468)
  O   difference = -0.0277  SE 0.0676  95% CI [-0.1603, +0.1048]  p=0.722
  B   difference = -0.0649  SE 0.0824  95% CI [-0.2264, +0.0966]  p=0.457
  =   the rival needs this POSITIVE and large; it is not => P2 FAILS
  = 
  = === shift-share decomposition of the fall in mean s ===
  =   novice share 46.7% -> 30.7%
  O   mean s: novice 2.724->2.266   established 2.752->2.401
  B   mean s: novice 2.373->1.877   established 2.438->2.094
  O   TOTAL   -0.3797
  B   TOTAL   -0.3803
  O   WITHIN  -0.3926  (103.4%)
  B   WITHIN  -0.4028  (105.9%)
  O   BETWEEN +0.0129  ( -3.4%)   <- the rival's share
  B   BETWEEN +0.0225  ( -5.9%)   <- the rival's share
  = 
  = === bounding the rival ===
  =   to explain the entire fall in mean s, novices would have to score +2.38 higher on a 0-4 scale
  O   point estimate                               -> between = +0.00443 =  -1.2% of the total
  B   point estimate                               -> between = +0.01036 =  -2.7% of the total
  O   95% CI bound most favourable to the rival    -> between = -0.01673 =  +4.4% of the total
  B   95% CI bound most favourable to the rival    -> between = -0.01543 =  +4.1% of the total
  = 
  = === dose-response (PPML, month-clustered) ===
  O   baseline, plain month FE                         gamma=-0.3759 (SE 0.0620)  p=1.36e-09
  B   baseline, plain month FE                         gamma=-0.2616 (SE 0.0406)  p=1.2e-10
  O   novice-x-month FE (absorbs the rival's shock)    gamma=-0.3911 (SE 0.0690)  p=1.42e-08
  B   novice-x-month FE (absorbs the rival's shock)    gamma=-0.2803 (SE 0.0442)  p=2.32e-10
  O   established askers only                          gamma=-0.3586 (SE 0.0648)  p=3.12e-08
  B   established askers only                          gamma=-0.2453 (SE 0.0463)  p=1.18e-07
  = 
  O written: E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\orig\02_estimation\asker_rival_test.json
  B written: E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\blind\02_estimation\asker_rival_test.json
  = 

## asker_tenure.log  (orig 48 lines, blind 48 lines)
  = labels: N=6000, months 2021-06..2026-05, s in [np.int64(0), np.int64(1), np.int64(2), np.int64(3), np.int64(4)]
  = [owners] have 6000, need 0
  = [users] have 5563, need 0
  = 
  = === (a) owner resolution ===
  = resolved 5877/6000 = 98.0%
  O   by bin:    {0: 1.0, 1: 0.9759, 2: 0.9792, 3: 0.9811, 4: 0.9807}  chi2 p=0.7865
  B   by bin:    {0: 0.968, 1: 0.9794, 2: 0.9785, 3: 0.9845, 4: 0.9777}  chi2 p=0.2251
  =   by period: {0: 0.9778, 1: 0.9802}  chi2 p=0.6052
  =   usable after tenure>=0: 5877
  = 
  = === (b) asker tenure, pre vs post ===
  =   pre  N= 1760  mean=  776.6d  median=  261.7d
  =   post N= 4117  mean= 1548.1d  median= 1009.9d
  =   Mann-Whitney p=1.4e-60
  =   share of askers with <1y account: 53.9% -> 35.5%
  = 
  = === (c) tenure vs substitutability ===
  O   Spearman rho=+0.0290, p=0.0264
  B   Spearman rho=+0.0568, p=1.33e-05
  =   pre-period tercile cuts: 36d, 763d
  =   mean s by stratum x period:
  = post       0      1
  = g                  
  O mid    2.671  2.345
  B mid    2.375  1.981
  O old    2.772  2.416
  B old    2.560  2.115
  O young  2.731  2.234
  B young  2.366  1.858
  = 
  = === (d) shift-share decomposition of the mean-s decline ===
  =   stratum shares pre : {'young': 0.3335, 'mid': 0.333, 'old': 0.3335}
  =   stratum shares post: {'young': 0.2256, 'mid': 0.2208, 'old': 0.5536}
  O   mean s pre : {'young': 2.7308, 'mid': 2.6706, 'old': 2.7717}
  B   mean s pre : {'young': 2.3663, 'mid': 2.3754, 'old': 2.5605}
  O   mean s post: {'young': 2.2336, 'mid': 2.3454, 'old': 2.4164}
  B   mean s post: {'young': 1.8579, 'mid': 1.9813, 'old': 2.115}
  O   TOTAL   change in mean s : -0.3649
  B   TOTAL   change in mean s : -0.4066
  O   WITHIN  (same-tenure askers ask fewer machine-answerable Qs): -0.3867  (106.0%)
  B   WITHIN  (same-tenure askers ask fewer machine-answerable Qs): -0.4489  (110.4%)
  O   BETWEEN (the tenure mix changed = the rival explanation)   : +0.0217  ( -6.0%)
  B   BETWEEN (the tenure mix changed = the rival explanation)   : +0.0422  (-10.4%)
  = 
  = === (e) the paper's dose-response, within tenure strata ===
  O   all resolved askers    gamma=-0.4163 (SE 0.0680)  p=9.21e-10   cells=240  s4/s1 diff=-71.3%
  B   all resolved askers    gamma=-0.3016 (SE 0.0390)  p=1.07e-14   cells=240  s4/s1 diff=-59.5%
  O   tenure = young         gamma=-0.4704 (SE 0.0790)  p=2.57e-09   cells=230  s4/s1 diff=-75.6%
  B   tenure = young         gamma=-0.3222 (SE 0.0622)  p=2.27e-07   cells=232  s4/s1 diff=-62.0%
  O   tenure = mid           gamma=-0.3454 (SE 0.1111)  p=0.00188   cells=236  s4/s1 diff=-64.5%
  B   tenure = mid           gamma=-0.2987 (SE 0.0767)  p=9.87e-05   cells=236  s4/s1 diff=-59.2%
  O   tenure = old           gamma=-0.4105 (SE 0.0819)  p=5.37e-07   cells=240  s4/s1 diff=-70.8%
  B   tenure = old           gamma=-0.3268 (SE 0.0529)  p=6.6e-10   cells=240  s4/s1 diff=-62.5%
  = 
  = === (e2) pooled, stratum-x-month FE (absorbs the rival's shock) ===
  O   cells=720, zero cells=1.9% -> Poisson (PPML), log-OLS would drop them
  B   cells=720, zero cells=1.7% -> Poisson (PPML), log-OLS would drop them
  O   PPML gamma (stratum-x-month FE) = -0.3923 (SE 0.0617), p=2.08e-10
  B   PPML gamma (stratum-x-month FE) = -0.3180 (SE 0.0406), p=5.17e-15
  O   PPML gamma (plain month FE, same cells) = -0.3685 (SE 0.0534), p=5.07e-12
  B   PPML gamma (plain month FE, same cells) = -0.2845 (SE 0.0345), p=1.79e-16
  = 
  O written: E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\orig\02_estimation\asker_tenure.json
  B written: E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\blind\02_estimation\asker_tenure.json
  = 

## bin_stability_test.log  (orig 62 lines, blind 62 lines)
  O N=6000  usable after exposure trim (<= 38 months post) = 5640
  B N=6000  usable after exposure trim (<= 38 months post) = 5201
  =   dropped: 45 without creation date, 300 inside the final 90-day window
  = 
  = === A. duplicate closure within 90 days, by bin x period ===
  =  bin   pre rate      n  post rate      n      diff               95% CI
  O s  1     3.69%    271     2.12%    945   -1.57%   [-4.00%, +0.85%]
  B s  1     4.58%    415     1.96%   1227   -2.62%   [-4.78%, -0.47%]
  O s  2     4.31%    394     2.48%   1090   -1.84%   [-4.05%, +0.37%]
  B s  2     4.42%    294     1.57%    699   -2.85%   [-5.37%, -0.32%]
  O s  3     4.69%    661     4.08%   1300   -0.61%   [-2.55%, +1.32%]
  B s  3     5.12%    586     5.46%   1081   +0.34%   [-1.90%, +2.58%]
  O s  4    11.83%    465    10.12%    514   -1.71%   [-5.64%, +2.21%]
  B s  4    12.32%    406    10.95%    493   -1.36%   [-5.58%, +2.86%]
  =   RIVAL predicts the low bins rise; EXIT predicts all four flat.
  = 
  = === B. does the closure-by-bin gradient flatten after the event? ===
  O   pre : Spearman rho=+0.1145 (p=1.2e-06)   LPM slope=+0.02623 (SE 0.00597)
  B   pre : Spearman rho=+0.1051 (p=1.4e-05)   LPM slope=+0.02250 (SE 0.00583)
  O   post: Spearman rho=+0.1079 (p=2e-11)   LPM slope=+0.02166 (SE 0.00360)
  B   post: Spearman rho=+0.1384 (p=2e-16)   LPM slope=+0.02635 (SE 0.00363)
  O   interaction s x post = -0.00457 (SE 0.00697), p = 0.512
  B   interaction s x post = +0.00386 (SE 0.00687), p = 0.575
  = 
  = === C. what the rival requires, quantified ===
  O   bin shares: {'s1': '0.151->0.246', 's2': '0.220->0.283', 's3': '0.369->0.338', 's4': '0.260->0.134'}
  B   bin shares: {'s1': '0.244->0.351', 's2': '0.173->0.200', 's3': '0.345->0.309', 's4': '0.239->0.141'}
  O   donor bins (those that lost share) had a pre-event duplicate rate of 10.41%
  B   donor bins (those that lost share) had a pre-event duplicate rate of 10.39%
  O   s1: under pure migration the post rate would be 6.27%; observed 2.12%  (NOT consistent)
  B   s1: under pure migration the post rate would be 6.35%; observed 1.96%  (NOT consistent)
  O   s2: under pure migration the post rate would be 5.67%; observed 2.48%  (NOT consistent)
  B   s2: under pure migration the post rate would be 5.23%; observed 1.57%  (NOT consistent)
  = 
  = === D. question length within bin (right-censored at ~1400 chars) ===
  O   text available for 5640/5640
  B   text available for 5201/5201
  =  bin  pre median  post median       MW p
  O s  1         500          613   7.54e-06
  B s  1         486          605   2.73e-12
  O s  2         491          636   2.87e-13
  B s  2         497          633   3.81e-09
  O s  3         472          572   3.75e-11
  B s  3         463          558    1.5e-09
  O s  4         373          498    2.3e-13
  B s  4         392          468   2.12e-05
  =   RIVAL predicts within-bin length rises (more context pasted in).
  = 
  = === E. answers and votes within bin (platform-native, no classifier) ===
  =  bin  ans pre  ans post  score pre  score post
  O s  1     0.90      0.80       0.38        0.45
  B s  1     1.08      0.94       0.48        0.43
  O s  2     1.03      0.93       0.51        0.52
  B s  2     1.12      1.00       0.43        0.57
  O s  3     1.28      1.22       0.43        0.60
  B s  3     1.24      1.15       0.57        0.61
  O s  4     1.61      1.54       0.83        0.58
  B s  4     1.62      1.56       0.68        0.60
  = 
  O written: E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\orig\02_estimation\bin_stability_test.json
  B written: E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\blind\02_estimation\bin_stability_test.json
  = 
  = === F. how much migration is compatible with the closure data? ===
  O   common moderation shift, estimated from the uncontaminated donor s4: -1.71%
  B   common moderation shift, estimated from the uncontaminated donor s4: -1.36%
  O   s1: migrated fraction f = +2.0%  (95% upper bound +15.7%);  pure migration would need f = 38.4%
  B   s1: migrated fraction f = -21.7%  (95% upper bound -8.3%);  pure migration would need f = 30.4%
  O        => migration can account for at most 41% of s1's share gain
  B        => migration can account for at most 0% of s1's share gain
  O   s2: migrated fraction f = -2.1%  (95% upper bound +13.1%);  pure migration would need f = 22.3%
  B   s2: migrated fraction f = -24.9%  (95% upper bound -9.4%);  pure migration would need f = 13.5%
  O        => migration can account for at most 59% of s2's share gain
  B        => migration can account for at most 0% of s2's share gain
  = 
  = === G. does the answers-per-question gradient survive? ===
  O   s slope pre  = +0.2456 (SE 0.0218)
  B   s slope pre  = +0.1681 (SE 0.0210)
  O   s x post     = -0.0033 (SE 0.0269), p = 0.904
  B   s x post     = +0.0035 (SE 0.0259), p = 0.894
  = 
  O rewritten: E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\orig\02_estimation\bin_stability_test.json
  B rewritten: E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\blind\02_estimation\bin_stability_test.json
  = 
  = === H. migration bound from answers per question (higher power) ===
  O   donor bins' pre-event mean answers = 1.542; common shift from s4 = -0.064
  B   donor bins' pre-event mean answers = 1.517; common shift from s4 = -0.058
  O   s1: f = -5.1%  (95% upper bound +2.4%);  pure migration needs 38.4%
  B   s1: f = -17.8%  (95% upper bound -7.7%);  pure migration needs 30.4%
  O        => migration explains at most 6% of s1's share gain
  B        => migration explains at most 0% of s1's share gain
  O   s2: f = -6.4%  (95% upper bound +2.0%);  pure migration needs 22.3%
  B   s2: f = -14.5%  (95% upper bound +1.7%);  pure migration needs 13.5%
  O        => migration explains at most 9% of s2's share gain
  B        => migration explains at most 12% of s2's share gain
  = 
  O rewritten: E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\orig\02_estimation\bin_stability_test.json
  B rewritten: E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\blind\02_estimation\bin_stability_test.json
  = 

## capability_ramp.log  (orig 77 lines, blind 77 lines)
  = 
  = == python ==
  =   (a) windowed DiD
  O     full 2022-12..2026-05            post_m=42  γ=-0.416 (SE 0.067) p=0.0000  s4-vs-s1=-71%
  B     full 2022-12..2026-05            post_m=42  γ=-0.304 (SE 0.038) p=0.0000  s4-vs-s1=-60%
  O     GPT-3.5 only 2022-12..2023-02    post_m= 3  γ=-0.203 (SE 0.169) p=0.2317  s4-vs-s1=-46%
  B     GPT-3.5 only 2022-12..2023-02    post_m= 3  γ=-0.000 (SE 0.048) p=0.9950  s4-vs-s1=-0%
  O     first 6m 2022-12..2023-05        post_m= 6  γ=-0.271 (SE 0.154) p=0.0787  s4-vs-s1=-56%
  B     first 6m 2022-12..2023-05        post_m= 6  γ=-0.113 (SE 0.073) p=0.1244  s4-vs-s1=-29%
  O     y1 2022-12..2023-11              post_m=12  γ=-0.313 (SE 0.102) p=0.0021  s4-vs-s1=-61%
  B     y1 2022-12..2023-11              post_m=12  γ=-0.193 (SE 0.058) p=0.0009  s4-vs-s1=-44%
  O     y2 2023-12..2024-11              post_m=12  γ=-0.499 (SE 0.087) p=0.0000  s4-vs-s1=-78%
  B     y2 2023-12..2024-11              post_m=12  γ=-0.387 (SE 0.047) p=0.0000  s4-vs-s1=-69%
  O     y3 2024-12..2025-11              post_m=12  γ=-0.447 (SE 0.071) p=0.0000  s4-vs-s1=-74%
  B     y3 2024-12..2025-11              post_m=12  γ=-0.343 (SE 0.047) p=0.0000  s4-vs-s1=-64%
  O     y4 2025-12..2026-05              post_m= 6  γ=-0.391 (SE 0.125) p=0.0017  s4-vs-s1=-69%
  B     y4 2025-12..2026-05              post_m= 6  γ=-0.281 (SE 0.050) p=0.0000  s4-vs-s1=-57%
  =   (b) event-study year-bucket means of γ_k (point estimates; inference is in (a))
  O     pre-leads mean vs ref 2022-11: -0.347 (17 months)
  B     pre-leads mean vs ref 2022-11: -0.133 (17 months)
  O     y1   months=12  mean γ_k vs ref=-0.640  vs pre-mean=-0.293
  B     y1   months=12  mean γ_k vs ref=-0.318  vs pre-mean=-0.186
  O     y2   months=12  mean γ_k vs ref=-0.827  vs pre-mean=-0.480
  B     y2   months=12  mean γ_k vs ref=-0.512  vs pre-mean=-0.379
  O     y3   months=12  mean γ_k vs ref=-0.775  vs pre-mean=-0.428
  B     y3   months=12  mean γ_k vs ref=-0.469  vs pre-mean=-0.336
  O     y4   months= 6  mean γ_k vs ref=-0.719  vs pre-mean=-0.372
  B     y4   months= 6  mean γ_k vs ref=-0.407  vs pre-mean=-0.274
  =   (c) absolute-volume domain (from 1.2): s4-vs-s1 volume-weighted differential by window
  O     full 2022-12..2026-05            platform=-76%  s1=-64%  s4=-86%  s4-vs-s1(vol-wt)=-62%
  B     full 2022-12..2026-05            platform=-76%  s1=-69%  s4=-84%  s4-vs-s1(vol-wt)=-51%
  O     GPT-3.5 only 2022-12..2023-02    platform=-25%  s1=-16%  s4=-51%  s4-vs-s1(vol-wt)=-42%
  B     GPT-3.5 only 2022-12..2023-02    platform=-25%  s1=-22%  s4=-23%  s4-vs-s1(vol-wt)=-1%
  O     first 6m 2022-12..2023-05        platform=-35%  s1=-21%  s4=-59%  s4-vs-s1(vol-wt)=-48%
  B     first 6m 2022-12..2023-05        platform=-35%  s1=-27%  s4=-44%  s4-vs-s1(vol-wt)=-23%
  O     y1 2022-12..2023-11              platform=-47%  s1=-29%  s4=-67%  s4-vs-s1(vol-wt)=-54%
  B     y1 2022-12..2023-11              platform=-47%  s1=-36%  s4=-60%  s4-vs-s1(vol-wt)=-38%
  O     y2 2023-12..2024-11              platform=-76%  s1=-56%  s4=-87%  s4-vs-s1(vol-wt)=-71%
  B     y2 2023-12..2024-11              platform=-76%  s1=-65%  s4=-89%  s4-vs-s1(vol-wt)=-69%
  O     y3 2024-12..2025-11              platform=-93%  s1=-89%  s4=-97%  s4-vs-s1(vol-wt)=-71%
  B     y3 2024-12..2025-11              platform=-93%  s1=-91%  s4=-97%  s4-vs-s1(vol-wt)=-65%
  O     y4 2025-12..2026-05              platform=-98%  s1=-97%  s4=-99%  s4-vs-s1(vol-wt)=-68%
  B     y4 2025-12..2026-05              platform=-98%  s1=-98%  s4=-99%  s4-vs-s1(vol-wt)=-52%
  = 
  = == javascript ==
  =   (a) windowed DiD
  =     full 2022-12..2026-05            post_m=42  γ=-0.229 (SE 0.067) p=0.0007  s4-vs-s1=-50%
  =     GPT-3.5 only 2022-12..2023-02    post_m= 3  γ=-0.015 (SE 0.106) p=0.8893  s4-vs-s1=-4%
  =     first 6m 2022-12..2023-05        post_m= 6  γ=-0.123 (SE 0.120) p=0.3043  s4-vs-s1=-31%
  =     y1 2022-12..2023-11              post_m=12  γ=-0.088 (SE 0.081) p=0.2781  s4-vs-s1=-23%
  =     y2 2023-12..2024-11              post_m=12  γ=-0.316 (SE 0.081) p=0.0001  s4-vs-s1=-61%
  =     y3 2024-12..2025-11              post_m=12  γ=-0.296 (SE 0.079) p=0.0002  s4-vs-s1=-59%
  =     y4 2025-12..2026-05              post_m= 6  γ=-0.203 (SE 0.112) p=0.0694  s4-vs-s1=-46%
  =   (b) event-study year-bucket means of γ_k (point estimates; inference is in (a))
  =     pre-leads mean vs ref 2022-11: +0.200 (17 months)
  =     y1   months=12  mean γ_k vs ref=+0.101  vs pre-mean=-0.099
  =     y2   months=12  mean γ_k vs ref=-0.127  vs pre-mean=-0.327
  =     y3   months=12  mean γ_k vs ref=-0.107  vs pre-mean=-0.307
  =     y4   months= 6  mean γ_k vs ref=-0.015  vs pre-mean=-0.214
  =   (c) absolute-volume domain (from 1.2): s4-vs-s1 volume-weighted differential by window
  =     full 2022-12..2026-05            platform=-79%  s1=-75%  s4=-81%  s4-vs-s1(vol-wt)=-23%
  =     GPT-3.5 only 2022-12..2023-02    platform=-28%  s1=-39%  s4=-21%  s4-vs-s1(vol-wt)=+30%
  =     first 6m 2022-12..2023-05        platform=-38%  s1=-38%  s4=-42%  s4-vs-s1(vol-wt)=-6%
  =     y1 2022-12..2023-11              platform=-50%  s1=-51%  s4=-53%  s4-vs-s1(vol-wt)=-4%
  =     y2 2023-12..2024-11              platform=-80%  s1=-69%  s4=-84%  s4-vs-s1(vol-wt)=-48%
  =     y3 2024-12..2025-11              platform=-96%  s1=-93%  s4=-96%  s4-vs-s1(vol-wt)=-49%
  =     y4 2025-12..2026-05              platform=-99%  s1=-98%  s4=-99%  s4-vs-s1(vol-wt)=-32%
  = 
  = == java ==
  =   (a) windowed DiD
  =     full 2022-12..2026-05            post_m=42  γ=-0.123 (SE 0.052) p=0.0185  s4-vs-s1=-31%
  =     GPT-3.5 only 2022-12..2023-02    post_m= 3  γ=-0.004 (SE 0.101) p=0.9675  s4-vs-s1=-1%
  =     first 6m 2022-12..2023-05        post_m= 6  γ=-0.066 (SE 0.070) p=0.3431  s4-vs-s1=-18%
  =     y1 2022-12..2023-11              post_m=12  γ=-0.092 (SE 0.066) p=0.1664  s4-vs-s1=-24%
  =     y2 2023-12..2024-11              post_m=12  γ=-0.204 (SE 0.057) p=0.0003  s4-vs-s1=-46%
  =     y3 2024-12..2025-11              post_m=12  γ=-0.191 (SE 0.067) p=0.0044  s4-vs-s1=-44%
  =     y4 2025-12..2026-05              post_m= 6  γ=+0.110 (SE 0.089) p=0.2200  s4-vs-s1=+39%
  =   (b) event-study year-bucket means of γ_k (point estimates; inference is in (a))
  =     pre-leads mean vs ref 2022-11: +0.174 (17 months)
  =     y1   months=12  mean γ_k vs ref=+0.073  vs pre-mean=-0.101
  =     y2   months=12  mean γ_k vs ref=-0.040  vs pre-mean=-0.214
  =     y3   months=12  mean γ_k vs ref=-0.026  vs pre-mean=-0.200
  =     y4   months= 6  mean γ_k vs ref=+0.274  vs pre-mean=+0.100
  =   (c) absolute-volume domain (from 1.2): s4-vs-s1 volume-weighted differential by window
  =     full 2022-12..2026-05            platform=-73%  s1=-69%  s4=-79%  s4-vs-s1(vol-wt)=-31%
  =     GPT-3.5 only 2022-12..2023-02    platform=-27%  s1=-30%  s4=-33%  s4-vs-s1(vol-wt)=-5%
  =     first 6m 2022-12..2023-05        platform=-33%  s1=-23%  s4=-40%  s4-vs-s1(vol-wt)=-21%
  =     y1 2022-12..2023-11              platform=-43%  s1=-38%  s4=-52%  s4-vs-s1(vol-wt)=-23%
  =     y2 2023-12..2024-11              platform=-74%  s1=-67%  s4=-82%  s4-vs-s1(vol-wt)=-45%
  =     y3 2024-12..2025-11              platform=-91%  s1=-89%  s4=-94%  s4-vs-s1(vol-wt)=-47%
  =     y4 2025-12..2026-05              platform=-97%  s1=-97%  s4=-96%  s4-vs-s1(vol-wt)=+28%
  = 
  O PASS full=-0.416: True (-0.4156);  PASS GPT-3.5=-0.203: True (-0.2027);  PASS event-study == manuscript csv (59 pts): True (max|diff|=1.6e-14)
  B PASS full=-0.416: False (-0.3038);  PASS GPT-3.5=-0.203: False (-0.0003);  PASS event-study == manuscript csv (59 pts): True (max|diff|=9.2e-15)
  O written: E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\orig\02_estimation\capability_ramp.json
  B written: E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\blind\02_estimation\capability_ramp.json
  O          E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\orig\02_estimation\capability_ramp_eventstudy.csv
  B          E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\blind\02_estimation\capability_ramp_eventstudy.csv
  = 

## check_cap_sensitivity.log  (orig 9 lines, blind 9 lines)
  = 标签 6000 条，能配上正文长度的 6000 条，触顶(≥1400) 312 条 = 5.2%
  = 触顶率：前期 2.6%，后期 6.3%
  O 触顶率按 bin（后期）： {0: 11.8, 1: 8.4, 2: 6.9, 3: 5.2, 4: 4.0}
  B 触顶率按 bin（后期）： {0: 16.9, 1: 7.1, 2: 5.8, 3: 4.0, 4: 2.1}
  O 全样本（应复现 −0.416）                    γ = -0.416 (SE 0.067), p = 6.7e-10,  N题 = 6000
  B 全样本（应复现 −0.416）                    γ = -0.304 (SE 0.038), p = 1.1e-15,  N题 = 6000
  O 剔除触顶问题                             γ = -0.414 (SE 0.068), p = 9.6e-10,  N题 = 5688
  B 剔除触顶问题                             γ = -0.292 (SE 0.038), p = 1.6e-14,  N题 = 5688
  O 剔除 ≥1,000 字符（更狠）                   γ = -0.425 (SE 0.071), p = 2.7e-09,  N题 = 5190
  B 剔除 ≥1,000 字符（更狠）                   γ = -0.278 (SE 0.038), p = 1.6e-13,  N题 = 5190
  = 
  O 触顶剔除后 γ 变化 +0.001（0%）
  B 触顶剔除后 γ 变化 +0.012（4%）
  = 

## check_detrend_ci.log  (orig 13 lines, blind 13 lines)
  = k 范围 -18..41，缺失的 k：[-1]
  O 前期(k<=-2) 17 个月：均值 -0.347，SD 0.194，min -0.68，max 0.04
  B 前期(k<=-2) 17 个月：均值 -0.133，SD 0.102，min -0.32，max 0.06
  O 后期(k>=0)  42 个月：均值 -0.743
  B 后期(k>=0)  42 个月：均值 -0.429
  O 后期均值 − 前期均值（=把参照换成前期均值）：-0.396
  B 后期均值 − 前期均值（=把参照换成前期均值）：-0.296
  = 
  O 前期线性趋势：截距 -0.391 (SE 0.110)，斜率 -0.0044/月 (SE 0.0098)，t = -0.45
  B 前期线性趋势：截距 -0.164 (SE 0.058)，斜率 -0.0031/月 (SE 0.0052)，t = -0.59
  O 外推的前期水平（后期均值处）：-0.482 (SE 0.304, 仅趋势拟合的不确定性)
  B 外推的前期水平（后期均值处）：-0.226 (SE 0.160, 仅趋势拟合的不确定性)
  O 去趋势后的后期均值：-0.262   （稿件表 3 写 −0.26）
  B 去趋势后的后期均值：-0.203   （稿件表 3 写 −0.26）
  O 只算趋势外推不确定性的 95% 区间：[-0.86, 0.33]
  B 只算趋势外推不确定性的 95% 区间：[-0.52, 0.11]
  O 再加后期均值的粗略 SE 0.033 → 合并 SE 0.306，区间 [-0.86, 0.34]
  B 再加后期均值的粗略 SE 0.022 → 合并 SE 0.161，区间 [-0.52, 0.11]
  = 
  O 结论线索：斜率 t=-0.45；外推 30 个月把一个不显著的斜率放大了 30 倍。
  B 结论线索：斜率 t=-0.59；外推 30 个月把一个不显著的斜率放大了 30 倍。
  = 

## closure_check.log  (orig 79 lines, blind 79 lines)
  = 
  = merged rows=6000  rows missing meta=5537
  = 
  = === (a) closure rate by substitutability bin x period ===
  =  s  post     mean  count
  O  0     0 0.000000      8
  B  0     0 0.040816     98
  O  0     1 0.176471     17
  B  0     1 0.059701    402
  O  1     0 0.047794    272
  B  1     0 0.055422    415
  O  1     1 0.049407   1012
  B  1     1 0.049512   1333
  O  2     0 0.048223    394
  B  2     0 0.067797    295
  O  2     1 0.053556   1195
  B  2     1 0.037516    773
  O  3     0 0.075643    661
  B  3     0 0.071672    586
  O  3     1 0.073257   1406
  B  3     1 0.081315   1156
  O  4     0 0.159140    465
  B  4     0 0.165025    406
  O  4     1 0.152632    570
  B  4     1 0.175373    536
  = 
  = === (a2) closure rate by bin x year-window (pre / y1(2022-12..2023-11) / y2(2023-12..2024-11) / y3+(2024-12..)) ===
  =  s        ybucket     mean  count
  O  0            pre 0.000000      8
  B  0            pre 0.040816     98
  O  0        y1_2023 1.000000      1
  B  0        y1_2023 0.075000     80
  O  0        y2_2024 0.000000      7
  B  0        y2_2024 0.036364    110
  O  0 y3plus_2025-26 0.222222      9
  B  0 y3plus_2025-26 0.066038    212
  O  1            pre 0.047794    272
  B  1            pre 0.055422    415
  O  1        y1_2023 0.039062    256
  B  1        y1_2023 0.028571    350
  O  1        y2_2024 0.039275    331
  B  1        y2_2024 0.039024    410
  O  1 y3plus_2025-26 0.063529    425
  B  1 y3plus_2025-26 0.069808    573
  O  2            pre 0.048223    394
  B  2            pre 0.067797    295
  O  2        y1_2023 0.039088    307
  B  2        y1_2023 0.024272    206
  O  2        y2_2024 0.048193    332
  B  2        y2_2024 0.044643    224
  O  2 y3plus_2025-26 0.064748    556
  B  2 y3plus_2025-26 0.040816    343
  O  3            pre 0.075643    661
  B  3            pre 0.071672    586
  O  3        y1_2023 0.037946    448
  B  3        y1_2023 0.040000    375
  O  3        y2_2024 0.082667    375
  B  3        y2_2024 0.099698    331
  O  3 y3plus_2025-26 0.094340    583
  B  3 y3plus_2025-26 0.102222    450
  O  4            pre 0.159140    465
  B  4            pre 0.165025    406
  O  4        y1_2023 0.117021    188
  B  4        y1_2023 0.137566    189
  O  4        y2_2024 0.174194    155
  B  4        y2_2024 0.192000    125
  O  4 y3plus_2025-26 0.167401    227
  B  4 y3plus_2025-26 0.198198    222
  = 
  = === (c) closure rate pre-2024 vs 2024+ (Staging Ground split), by bin ===
  =  s period2024     mean  count
  O  0      2024+ 0.125000     16
  B  0      2024+ 0.057143    315
  O  0    pre2024 0.111111      9
  B  0    pre2024 0.054054    185
  O  1      2024+ 0.055096    726
  B  1      2024+ 0.059197    946
  O  1    pre2024 0.041219    558
  B  1    pre2024 0.041147    802
  O  2      2024+ 0.059908    868
  B  2      2024+ 0.044037    545
  O  2    pre2024 0.042996    721
  B  2    pre2024 0.047801    523
  O  3      2024+ 0.092176    933
  B  3      2024+ 0.101717    757
  O  3    pre2024 0.059083   1134
  B  3    pre2024 0.059898    985
  O  4      2024+ 0.173669    357
  B  4      2024+ 0.198813    337
  O  4    pre2024 0.146018    678
  B  4    pre2024 0.155372    605
  = 
  = === differential closure logit: closed ~ s*post ===
  = ==============================================================================
  =                  coef    std err          z      P>|z|      [0.025      0.975]
  = ------------------------------------------------------------------------------
  O Intercept     -3.9824      0.314    -12.699      0.000      -4.597      -3.368
  B Intercept     -3.4283      0.240    -14.290      0.000      -3.899      -2.958
  O s              0.5523      0.096      5.760      0.000       0.364       0.740
  B s              0.4018      0.078      5.170      0.000       0.249       0.554
  O post           0.4383      0.359      1.220      0.222      -0.266       1.142
  B post          -0.0009      0.278     -0.003      0.997      -0.546       0.545
  O s:post        -0.1548      0.114     -1.361      0.173      -0.378       0.068
  B s:post        -0.0096      0.093     -0.104      0.918      -0.192       0.173
  = ==============================================================================
  = 
  O [note] dropping 25 s=0 rows to match manuscript spec (s in 1..4) before regression
  B [note] dropping 500 s=0 rows to match manuscript spec (s in 1..4) before regression
  = 
  = === (b) dose-response re-estimated excluding closed questions (month size now free) ===
  =   bin-months with zero count after exclusion: 0 (dropped from log spec)
  O   OLS log-count (closed excluded): γ=-0.4120 (SE 0.0714) p=7.947e-09  s4-vs-s1=-70.9%
  B   OLS log-count (closed excluded): γ=-0.3113 (SE 0.0418) p=9.741e-14  s4-vs-s1=-60.7%
  O   Poisson/PPML (closed excluded, zeros included): γ=-0.3623 (SE 0.0644) p=1.868e-08
  B   Poisson/PPML (closed excluded, zeros included): γ=-0.2943 (SE 0.0405) p=3.678e-13
  = 
  O   [reference] OLS log-count (closed INCLUDED, same merged sample): γ=-0.4156 (SE 0.0673) p=6.691e-10
  B   [reference] OLS log-count (closed INCLUDED, same merged sample): γ=-0.3038 (SE 0.0379) p=1.07e-15
  = 
  = === (c) dose-response excluding closed, split pre-2024 / 2024+ ===
  O   pre-2024 post-period only    γ=-0.3024 (SE 0.1015) p=0.002883  n_post_months=13
  B   pre-2024 post-period only    γ=-0.2088 (SE 0.0609) p=0.0006025  n_post_months=13
  O   2024+ post-period only       γ=-0.4612 (SE 0.0716) p=1.207e-10  n_post_months=29
  B   2024+ post-period only       γ=-0.3572 (SE 0.0410) p=2.966e-18  n_post_months=29
  = 
  O overall closure rate in sample: 7.7%
  B overall closure rate in sample: 7.9%
  = 
  O written: E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\orig\02_estimation\closure_check.json
  B written: E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\blind\02_estimation\closure_check.json
  = 

## cross_family_analysis.log  (orig 26 lines, blind 26 lines)
  = model=glm-4.6: GLM labels for 5999/6000 (missing 1)
  = 
  O (1) GLM vs Claude, N=5999: binary κ=0.695 (raw 84.8%); weighted κ=0.756; exact 59.6%; ±1 94.5%
  B (1) GLM vs Claude, N=5999: binary κ=0.613 (raw 80.7%); weighted κ=0.685; exact 50.2%; ±1 88.8%
  O     off 2–3 boundary (n=2344): 96.9%;  on boundary (n=3655): 77.0%
  B     off 2–3 boundary (n=3189): 90.1%;  on boundary (n=2810): 70.0%
  O     score distributions  Claude: {0: 25, 1: 1284, 2: 1589, 3: 2066, 4: 1035}  GLM: {0: 11, 1: 2166, 2: 859, 3: 1649, 4: 1314}
  B     score distributions  Claude: {0: 500, 1: 1748, 2: 1068, 3: 1742, 4: 941}  GLM: {0: 11, 1: 2166, 2: 859, 3: 1649, 4: 1314}
  =     confusion (rows Claude 0-4, cols GLM 0-4):
  O  glm    0     1    2     3    4
  B  glm    0     1    2    3    4
  O score                         
  B score                        
  O 0      2    20    0     0    3
  B 0      5   409   54   17   15
  O 1      5  1166   92    19    2
  B 1      2  1142  362  204   38
  O 2      2   743  480   322   42
  B 2      2   373  248  364   81
  O 3      2   210  266  1123  465
  B 3      2   217  178  892  453
  O 4      0    27   21   185  802
  B 4      0    25   17  172  727
  O (4) agreement drift pre 84.1% vs post 85.0%, Fisher p=0.347
  B (4) agreement drift pre 81.8% vs post 80.2%, Fisher p=0.175
  = 
  = (2) GLM vs human consensus, N=300: binary κ=0.526 [0.430, 0.621] (raw 76.3%)  — Claude: κ=0.512 [0.413, 0.607]
  =     on agreed questions (N=230): κ=0.618 (80.9%)
  =     on adjudicated questions (N=70): κ=0.258 (61.4%)
  = 
  = (3) dose-response with GLM labels (s0 dropped; 0 empty bin-months absent from log spec):
  =     OLS γ=-0.227 (SE 0.036) p=4.90e-10  s4-vs-s1=-49%   Poisson γ=-0.180 (SE 0.038) p=1.56e-06   [Claude labels: −0.416]
  O E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\orig\05_additional_checks\cross_family_analysis.py:145: DeprecationWarning: DataFrameGroupBy.apply operated on the grouping columns. This behavior is deprecated, and in a future version of pandas the grouping columns will be excluded from the operation. Either pass `include_groups=False` to exclude the groupings or explicitly select the grouping columns after groupby to silence this warning.
  B E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\blind\05_additional_checks\cross_family_analysis.py:145: DeprecationWarning: DataFrameGroupBy.apply operated on the grouping columns. This behavior is deprecated, and in a future version of pandas the grouping columns will be excluded from the operation. Either pass `include_groups=False` to exclude the groupings or explicitly select the grouping columns after groupby to silence this warning.
  =   gs = dd.groupby("post").apply(lambda x: (x.glm >= 3).mean())
  =     GLM generative share pre 0.565 → post 0.465   [Claude: .63 → .47]
  = 
  O written: E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\orig\05_additional_checks\glm_relabel\cross_family_glm-4.6.json
  B written: E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\blind\05_additional_checks\glm_relabel\cross_family_glm-4.6.json

## edit_exposure_check.log  (orig 20 lines, blind 20 lines)
  O N=5930  pre=1791  post=4139
  B N=5467  pre=1701  post=3766
  = 
  = === A. edit incidence and timing ===
  O   pre : edited 53.0%   median days-to-last-edit 0   edited within 30d 93.3%   after 1y 3.3%
  B   pre : edited 52.6%   median days-to-last-edit 0   edited within 30d 93.5%   after 1y 3.1%
  O   post: edited 60.4%   median days-to-last-edit 0   edited within 30d 93.1%   after 1y 1.4%
  B   post: edited 60.2%   median days-to-last-edit 0   edited within 30d 93.1%   after 1y 1.5%
  O   late (>1y) edits: pre 1.7%  post 0.9%
  B   late (>1y) edits: pre 1.6%  post 0.9%
  = 
  = === B. does edit status move the score, within period? ===
  O   pre  edited   : unedited 2.805 (N=842)  edited 2.677 (N=949)  gap -0.129 [-0.222,-0.035]
  B   pre  edited   : unedited 2.623 (N=807)  edited 2.537 (N=894)  gap -0.086 [-0.191,+0.018]
  O   pre  late_edit: unedited 2.736 (N=1760)  edited 2.806 (N=31)  gap +0.071 [-0.266,+0.407]
  B   pre  late_edit: unedited 2.578 (N=1673)  edited 2.571 (N=28)  gap -0.007 [-0.419,+0.405]
  O   post edited   : unedited 2.424 (N=1639)  edited 2.337 (N=2500)  gap -0.087 [-0.149,-0.025]
  B   post edited   : unedited 2.250 (N=1500)  edited 2.235 (N=2266)  gap -0.015 [-0.086,+0.055]
  O   post late_edit: unedited 2.368 (N=4103)  edited 2.806 (N=36)  gap +0.438 [+0.136,+0.740]
  B   post late_edit: unedited 2.237 (N=3732)  edited 2.676 (N=34)  gap +0.440 [+0.166,+0.713]
  O   OLS s ~ edited*post : edited -0.129 (p=0.007)  edited:post +0.042 (p=0.464)
  B   OLS s ~ edited*post : edited -0.086 (p=0.105)  edited:post +0.071 (p=0.269)
  = 
  = === C. counterfactual bound: how much of the mean-s fall could exposure explain? ===
  O   edited   : edit-rate change 0.530->0.604, pre gap -0.129  => attributable +0.0095 of total -0.3654 (-2.6%)
  B   edited   : edit-rate change 0.526->0.602, pre gap -0.086  => attributable +0.0066 of total -0.3371 (-2.0%)
  O   late_edit: edit-rate change 0.017->0.009, pre gap +0.071  => attributable +0.0006 of total -0.3654 (-0.2%)
  B   late_edit: edit-rate change 0.016->0.009, pre gap -0.007  => attributable -0.0000 of total -0.3371 (+0.0%)
  = 
  = written: edit_exposure_check.json
  = 

## fixed_window_answer.log  (orig 13 lines, blind 13 lines)
  O N with fetched answers = 5,975
  B N with fetched answers = 5,500
  = 
  = FIXED-WINDOW answer margin (clean; identification within-month across bins):
  O     s1 answered within 30d: 0.662 -> 0.587
  B     s1 answered within 30d: 0.761 -> 0.681
  O     s4 answered within 30d: 0.886 -> 0.886
  B     s4 answered within 30d: 0.906 -> 0.888
  O   answered within 30d: score*post = +0.0258 (se 0.0138, p=0.06049)  ->  stays exploratory
  B   answered within 30d: score*post = +0.0277 (se 0.0121, p=0.02164)  ->  stays exploratory
  = 
  O     s1 answered within 90d: 0.669 -> 0.610
  B     s1 answered within 90d: 0.769 -> 0.703
  O     s4 answered within 90d: 0.888 -> 0.889
  B     s4 answered within 90d: 0.906 -> 0.896
  O   answered within 90d: score*post = +0.0227 (se 0.0129, p=0.07732)  ->  stays exploratory
  B   answered within 90d: score*post = +0.0238 (se 0.0120, p=0.04693)  ->  stays exploratory
  = 
  O first-answer latency among answered (N=4,728): pre median 0.0d, post 0.1d
  B first-answer latency among answered (N=4,431): pre median 0.0d, post 0.1d
  = 

## p0_2_staging_ground.log  (orig 34 lines, blind 34 lines)
  = N = 6000（应为 6,000）
  = closed_date 缺失（未关闭）5537，非缺失（已关闭）463
  = 
  = [Pre-ChatGPT vs Post]
  =   s   pre%%(N)              post%%(N)
  O   s1   4.78 (N= 272)       4.94 (N=1012)
  B   s1   5.54 (N= 415)       4.95 (N=1333)
  O   s2   4.82 (N= 394)       5.36 (N=1195)
  B   s2   6.78 (N= 295)       3.75 (N= 773)
  O   s3   7.56 (N= 661)       7.33 (N=1406)
  B   s3   7.17 (N= 586)       8.13 (N=1156)
  O   s4  15.91 (N= 465)      15.26 (N= 570)
  B   s4  16.50 (N= 406)      17.54 (N= 536)
  O   核对发表值 -> OK 吻合
  B   核对发表值 -> !! 不吻合 got=[np.float64(5.5), np.float64(6.8), np.float64(7.2), np.float64(16.5)]/[np.float64(5.0), np.float64(3.8), np.float64(8.1), np.float64(17.5)]
  = 
  = [现行切点 2024-07（发表值）]
  =   s   before%%(N)          after%%(N)
  O   s1   3.29 (N= 456)       6.29 (N= 556)
  B   s1   2.90 (N= 587)       6.57 (N= 746)
  O   s2   4.58 (N= 480)       5.87 (N= 715)
  B   s2   3.82 (N= 340)       3.70 (N= 433)
  O   s3   4.99 (N= 661)       9.40 (N= 745)
  B   s3   6.28 (N= 573)       9.95 (N= 583)
  O   s4  13.42 (N= 298)      17.28 (N= 272)
  B   s4  14.51 (N= 255)      20.28 (N= 281)
  O   核对发表值 before=[3.3, 4.6, 5.0, 13.4] after=[6.3, 5.9, 9.4, 17.3] -> OK 吻合
  B   核对发表值 before=[3.3, 4.6, 5.0, 13.4] after=[6.3, 5.9, 9.4, 17.3] -> !! 不吻合 got_b=[np.float64(2.9), np.float64(3.8), np.float64(6.3), np.float64(14.5)] got_a=[np.float64(6.6), np.float64(3.7), np.float64(9.9), np.float64(20.3)]
  = 
  = [官方切点 2024-06（订正后，供表 7 采用）]
  =   s   before%%(N)          after%%(N)
  O   s1   3.24 (N= 432)       6.21 (N= 580)
  B   s1   2.37 (N= 549)       6.76 (N= 784)
  O   s2   4.68 (N= 449)       5.76 (N= 746)
  B   s2   3.74 (N= 321)       3.76 (N= 452)
  O   s3   4.15 (N= 626)       9.87 (N= 780)
  B   s3   5.90 (N= 542)      10.10 (N= 614)
  O   s4  13.49 (N= 289)      17.08 (N= 281)
  B   s4  14.57 (N= 247)      20.07 (N= 289)
  = 
  = [Panel B 梯度：旧切点 2024-07 vs 新切点 2024-06]
  O   旧切点 before(2022-12..2024-06)           19 月  gamma=-0.3502  SE=0.0806  p=1.4e-05  核对发表值 gamma=-0.349 SE=0.086 -> OK 接近
  B   旧切点 before(2022-12..2024-06)           19 月  gamma=-0.2741  SE=0.0549  p=5.9e-07  核对发表值 gamma=-0.349 SE=0.086 -> 差值 dg=0.0749 dse=-0.0311
  O   旧切点 after(2024-07..2026-05)            23 月  gamma=-0.4696  SE=0.0738  p=2e-10  核对发表值 gamma=-0.464 SE=0.077 -> OK 接近
  B   旧切点 after(2024-07..2026-05)            23 月  gamma=-0.3284  SE=0.0377  p=3.3e-18  核对发表值 gamma=-0.464 SE=0.077 -> 差值 dg=0.1356 dse=-0.0393
  O   新切点 before(2022-12..2024-05)           18 月  gamma=-0.3410  SE=0.0822  p=3.4e-05
  B   新切点 before(2022-12..2024-05)           18 月  gamma=-0.2626  SE=0.0554  p=2.2e-06
  O   新切点 after(2024-06..2026-05)            24 月  gamma=-0.4715  SE=0.0725  p=7.9e-11
  B   新切点 after(2024-06..2026-05)            24 月  gamma=-0.3347  SE=0.0378  p=7.6e-19
  = 
  O 写入 E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\orig\02_estimation\review_r1\p0_2_staging_ground.json
  B 写入 E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\blind\02_estimation\review_r1\p0_2_staging_ground.json
  = 

## p0_3_placebo_overlap.log  (orig 21 lines, blind 21 lines)
  = ==============================================================================
  = P0-3：安慰剂窗口 vs 处理期重叠核验（±9 与 ±12）
  = ==============================================================================
  = 
  = ±9 月窗口：候选 43 个，事件前候选 9 个，其中窗口整段不碰处理期的 1 个
  O   真实事件 gamma=-0.3005，在 43 个候选里排第 2（第 4.7 百分位，越靠前越负）
  B   真实事件 gamma=-0.1450，在 43 个候选里排第 13（第 30.2 百分位，越靠前越负）
  =   事件前候选中比真实事件更负的：0/9
  O   写入 E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\orig\02_estimation\review_r1_reviewer_response_scripts\placebo_overlap_w9.csv
  B   写入 E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\blind\02_estimation\review_r1_reviewer_response_scripts\placebo_overlap_w9.csv
  = 
  = ±12 月窗口：候选 37 个，事件前候选 6 个，其中窗口整段不碰处理期的 0 个
  O   真实事件 gamma=-0.3163，在 37 个候选里排第 2（第 5.4 百分位，越靠前越负）
  B   真实事件 gamma=-0.1788，在 37 个候选里排第 13（第 35.1 百分位，越靠前越负）
  =   事件前候选中比真实事件更负的：0/6
  O   写入 E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\orig\02_estimation\review_r1_reviewer_response_scripts\placebo_overlap_w12.csv
  B   写入 E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\blind\02_estimation\review_r1_reviewer_response_scripts\placebo_overlap_w12.csv
  = 
  O 写入 E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\orig\02_estimation\review_r1_reviewer_response_scripts\p0_3_placebo_overlap_summary.json
  B 写入 E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\blind\02_estimation\review_r1_reviewer_response_scripts\p0_3_placebo_overlap_summary.json
  = 
  = 稿件现文本核对：
  =   §7.1 写 'nine placebo cutoffs precede it'                      -> 实际事件前候选 9 个（±9）
  =   §7.1 写 'more negative than every one of the nine placebo'     -> 整段不碰处理期的只有 1 个（±9）
  =   ±12 版本：事件前候选 6 个，整段干净的 0 个
  = 

## p0_6_pretrends.log  (orig 30 lines, blind 30 lines)
  O [1] 月度 gamma_k 重建 vs 归档文件：59 个月匹配，最大差 = 1.57e-14  -> OK 一致
  B [1] 月度 gamma_k 重建 vs 归档文件：59 个月匹配，最大差 = 9.21e-15  -> OK 一致
  O [1'] 月聚类 SE 是否退化（抽查前 5 个月度系数）：True（前 5 个 SE=[np.float64(0.0), np.float64(0.0), np.float64(0.0), np.float64(0.0), np.float64(nan)]）
  B [1'] 月聚类 SE 是否退化（抽查前 5 个月度系数）：True（前 5 个 SE=[np.float64(nan), np.float64(nan), np.float64(nan), np.float64(nan), np.float64(nan)]）
  = 
  = [2] 前期三窗口回归（非退化聚类 SE）：
  O   pre W1 2021-06..2021-11     6 月  beta=-0.3354  SE=0.0982  t=-3.42
  B   pre W1 2021-06..2021-11     6 月  beta=-0.0973  SE=0.0504  t=-1.93
  O   pre W2 2021-12..2022-05     6 月  beta=-0.3430  SE=0.1139  t=-3.01
  B   pre W2 2021-12..2022-05     6 月  beta=-0.1773  SE=0.0596  t=-2.98
  O   pre W3 2022-06..2022-10     5 月  beta=-0.3663  SE=0.0697  t=-5.26
  B   pre W3 2022-06..2022-10     5 月  beta=-0.1223  SE=0.0216  t=-5.65
  =   月聚类 SE 是否退化（应为否）：False
  = 
  = [3] 联合 Wald 检验  H0: beta_W1=beta_W2=beta_W3=0
  O   W = 48.377, df = 3, p = 0.0000
  B   W = 44.523, df = 3, p = 0.0000
  =   结论：拒绝——前期存在联合显著的斜率变化
  =   scale=0.0  (最远窗口偏离 = 0.0 个最小SE)  ncp=0.00  功效=0.050
  O   scale=0.5  (最远窗口偏离 = 1.5 个最小SE)  ncp=2.75  功效=0.254
  B   scale=0.5  (最远窗口偏离 = 1.5 个最小SE)  ncp=2.43  功效=0.227
  O   scale=1.0  (最远窗口偏离 = 3.0 个最小SE)  ncp=11.00  功效=0.804
  B   scale=1.0  (最远窗口偏离 = 3.0 个最小SE)  ncp=9.71  功效=0.747
  O   scale=2.0  (最远窗口偏离 = 6.0 个最小SE)  ncp=44.00  功效=1.000
  B   scale=2.0  (最远窗口偏离 = 6.0 个最小SE)  ncp=38.85  功效=1.000
  O   scale=4.0  (最远窗口偏离 = 12.0 个最小SE)  ncp=176.00  功效=1.000
  B   scale=4.0  (最远窗口偏离 = 12.0 个最小SE)  ncp=155.39  功效=1.000
  = 
  O   默认备择下的功效 = 0.804
  B   默认备择下的功效 = 0.747
  =   解读：功效尚可——'前期没查出联合显著'在这个备择规模下确有一定说服力
  = 
  = [自检]
  O   a) 1-cdf 与 sf 应等价：|0.0000000002 - 0.0000000002| = 4.72e-17 -> OK
  B   a) 1-cdf 与 sf 应等价：|0.0000000012 - 0.0000000012| = 4.70e-17 -> OK
  O   b) 功效随备择规模单调不减：True  序列=[np.float64(0.05), np.float64(0.254), np.float64(0.804), np.float64(1.0), np.float64(1.0)]
  B   b) 功效随备择规模单调不减：True  序列=[np.float64(0.05), np.float64(0.227), np.float64(0.747), np.float64(1.0), np.float64(1.0)]
  =   c) scale=0 功效应≈alpha=0.05：得 0.0500 -> OK
  = 
  = 自检总结：全部通过
  = 
  O 写入 E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\orig\02_estimation\review_r1\p0_6_pretrends.json
  B 写入 E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\blind\02_estimation\review_r1\p0_6_pretrends.json
  = 

## p0_6_ref_sensitivity.log  (orig 46 lines, blind 46 lines)
  = ==============================================================================
  = 先确认参照月本身是不是异常值（不看回归，直接看原始面板）
  = ==============================================================================
  O   2022-11（REF）mean_s = 2.980
  B   2022-11（REF）mean_s = 2.723
  O   前 6 个月（2022-05..2022-10）mean_s：[2.76, 2.76, 2.77, 2.54, 2.91, 2.6]，均值 2.723，SD 0.133
  B   前 6 个月（2022-05..2022-10）mean_s：[2.44, 2.63, 2.49, 2.57, 2.61, 2.61]，均值 2.559，SD 0.077
  O   2022-11 相对前 6 个月的 z 分数 = 1.93（|z|>1.5 视为可疑偏高）
  B   2022-11 相对前 6 个月的 z 分数 = 2.13（|z|>1.5 视为可疑偏高）
  = 
  = ==============================================================================
  = 稳健性：换不同参照，看'前期显著非零'这个结论还在不在
  = ==============================================================================
  = 
  = [V0 原版：参照=2022-11 单月]  参照 = ['2022-11']
  O   W1   (6月, 2021-06..2021-11)  beta=-0.3354  SE=0.0982  t=-3.42
  B   W1   (6月, 2021-06..2021-11)  beta=-0.0973  SE=0.0504  t=-1.93
  O   W2   (6月, 2021-12..2022-05)  beta=-0.3430  SE=0.1139  t=-3.01
  B   W2   (6月, 2021-12..2022-05)  beta=-0.1773  SE=0.0596  t=-2.98
  O   W3   (5月, 2022-06..2022-10)  beta=-0.3663  SE=0.0697  t=-5.26
  B   W3   (5月, 2022-06..2022-10)  beta=-0.1223  SE=0.0216  t=-5.65
  O   联合 Wald: W=48.38 df=3 p=0.0000  -> 显著非零
  B   联合 Wald: W=44.52 df=3 p=0.0000  -> 显著非零
  = 
  = [V1：参照=2022年9-11月三月均值]  参照 = ['2022-09', '2022-10', '2022-11']
  O   W1   (6月, 2021-06..2021-11)  beta=-0.1135  SE=0.1729  t=-0.66
  B   W1   (6月, 2021-06..2021-11)  beta=-0.0289  SE=0.0614  t=-0.47
  O   W2   (6月, 2021-12..2022-05)  beta=-0.1211  SE=0.1823  t=-0.66
  B   W2   (6月, 2021-12..2022-05)  beta=-0.1088  SE=0.0691  t=-1.57
  O   W3   (3月, 2022-06..2022-08)  beta=-0.1667  SE=0.1603  t=-1.04
  B   W3   (3月, 2022-06..2022-08)  beta=-0.0668  SE=0.0480  t=-1.39
  O   联合 Wald: W=1.11 df=3 p=0.7754  -> 不能拒绝为零
  B   联合 Wald: W=3.34 df=3 p=0.3425  -> 不能拒绝为零
  = 
  = [V2：参照=2022年6-11月六月均值]  参照 = ['2022-06', '2022-07', '2022-08', '2022-09', '2022-10', '2022-11']
  O   W1   (6月, 2021-06..2021-11)  beta=-0.0301  SE=0.1323  t=-0.23
  B   W1   (6月, 2021-06..2021-11)  beta=+0.0046  SE=0.0578  t=+0.08
  O   W2   (6月, 2021-12..2022-05)  beta=-0.0377  SE=0.1442  t=-0.26
  B   W2   (6月, 2021-12..2022-05)  beta=-0.0754  SE=0.0658  t=-1.15
  O   联合 Wald: W=0.09 df=2 p=0.9583  -> 不能拒绝为零
  B   联合 Wald: W=1.43 df=2 p=0.4888  -> 不能拒绝为零
  = 
  = ==============================================================================
  = V3：不设任何单独参照——直接检验三窗口彼此是否有别（H0: W1=W2=W3）
  = ==============================================================================
  =   以 W1(6月, 2021-06..2021-11) 为参照：
  O   W2 相对 W1: beta=-0.0076 SE=0.1489
  B   W2 相对 W1: beta=-0.0799 SE=0.0772
  O   W3 相对 W1: beta=+0.0301 SE=0.1323
  B   W3 相对 W1: beta=-0.0046 SE=0.0578
  O   联合检验 H0: W2=W1 且 W3=W1（即前期内部无结构）：W=0.09 df=2 p=0.9583 -> 不能拒绝——前期内部平坦，窗口间无显著差异
  B   联合检验 H0: W2=W1 且 W3=W1（即前期内部无结构）：W=1.43 df=2 p=0.4888 -> 不能拒绝——前期内部平坦，窗口间无显著差异
  = 
  = ==============================================================================
  = 汇总：三种不同参照下，'联合非零'检验的 p 值
  = ==============================================================================
  O   V0 原版：参照=2022-11 单月              W= 48.38  p=1.77e-10
  B   V0 原版：参照=2022-11 单月              W= 44.52  p=1.17e-09
  O   V1：参照=2022年9-11月三月均值             W=  1.11  p=7.75e-01
  B   V1：参照=2022年9-11月三月均值             W=  3.34  p=3.43e-01
  O   V2：参照=2022年6-11月六月均值             W=  0.09  p=9.58e-01
  B   V2：参照=2022年6-11月六月均值             W=  1.43  p=4.89e-01
  O   V3（窗口互比，不涉及参照月绝对水平）             W=  0.09  p=0.9583
  B   V3（窗口互比，不涉及参照月绝对水平）             W=  1.43  p=0.4888
  = 
  O 写入 E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\orig\02_estimation\review_r1\p0_6_ref_sensitivity.json
  B 写入 E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\blind\02_estimation\review_r1\p0_6_ref_sensitivity.json
  = 

## p1_14_bin_dummies.log  (orig 50 lines, blind 41 lines)
  = ============================================================================================
  = P1-14：连续剂量 vs 分组虚拟变量
  = ============================================================================================
  = 
  = --- python ---
  O   连续型 γ = -0.4156 (SE 0.0673)   稿件发表值 -0.416  -> OK 复现
  B   连续型 γ = -0.3038 (SE 0.0379)   稿件发表值 -0.416  -> !! 对不上，后续不可用
  O   分组虚拟变量（s1 为参照）：
  B 
  O       bin   δ（相对 s1）        SE       p        线性预测 (b−1)·γ     偏离
  B --- javascript ---
  O       s2    -0.2580    0.1858   0.1648       -0.4156        +0.1576
  B   连续型 γ = -0.2288 (SE 0.0674)   稿件发表值 -0.229  -> OK 复现
  O       s3    -0.6298    0.1636   0.0001       -0.8312        +0.2014
  B   分组虚拟变量（s1 为参照）：
  O       s4    -1.2614    0.2216   0.0000       -1.2468        -0.0146
  B       bin   δ（相对 s1）        SE       p        线性预测 (b−1)·γ     偏离
  O   线性约束 Wald 检验 (H0: δ3=2δ2 且 δ4=3δ2)：χ²(2) = 3.675, p = 0.1592
  B       s2    -0.3112    0.2798   0.2662       -0.2288        -0.0823
  O       -> 不能拒绝线性——把序数当等距在本数据上没有暴露问题
  B       s3    -0.6409    0.2318   0.0057       -0.4577        -0.1832
  O   相对 s1 的变化：s2 -22.7%   s3 -46.7%   s4 -71.7%   单调递减：是
  B       s4    -0.6529    0.2286   0.0043       -0.6865        +0.0336
  O 
  B   线性约束 Wald 检验 (H0: δ3=2δ2 且 δ4=3δ2)：χ²(2) = 3.879, p = 0.1437
  O --- javascript ---
  B       -> 不能拒绝线性——把序数当等距在本数据上没有暴露问题
  O   连续型 γ = -0.2288 (SE 0.0674)   稿件发表值 -0.229  -> OK 复现
  B   相对 s1 的变化：s2 -26.7%   s3 -47.3%   s4 -47.9%   单调递减：是
  O   分组虚拟变量（s1 为参照）：
  B 
  O       bin   δ（相对 s1）        SE       p        线性预测 (b−1)·γ     偏离
  B --- java ---
  O       s2    -0.3112    0.2798   0.2662       -0.2288        -0.0823
  B   连续型 γ = -0.1233 (SE 0.0524)   稿件发表值 -0.123  -> OK 复现
  O       s3    -0.6409    0.2318   0.0057       -0.4577        -0.1832
  B   分组虚拟变量（s1 为参照）：
  O       s4    -0.6529    0.2286   0.0043       -0.6865        +0.0336
  B       bin   δ（相对 s1）        SE       p        线性预测 (b−1)·γ     偏离
  O   线性约束 Wald 检验 (H0: δ3=2δ2 且 δ4=3δ2)：χ²(2) = 3.879, p = 0.1437
  B       s2    -0.1701    0.1493   0.2544       -0.1233        -0.0468
  O       -> 不能拒绝线性——把序数当等距在本数据上没有暴露问题
  B       s3    -0.2885    0.1277   0.0239       -0.2467        -0.0418
  O   相对 s1 的变化：s2 -26.7%   s3 -47.3%   s4 -47.9%   单调递减：是
  B       s4    -0.3717    0.1750   0.0337       -0.3700        -0.0017
  O 
  B   线性约束 Wald 检验 (H0: δ3=2δ2 且 δ4=3δ2)：χ²(2) = 0.113, p = 0.9450
  O --- java ---
  B       -> 不能拒绝线性——把序数当等距在本数据上没有暴露问题
  O   连续型 γ = -0.1233 (SE 0.0524)   稿件发表值 -0.123  -> OK 复现
  B   相对 s1 的变化：s2 -15.6%   s3 -25.1%   s4 -31.0%   单调递减：是
  O   分组虚拟变量（s1 为参照）：
  B 
  O       bin   δ（相对 s1）        SE       p        线性预测 (b−1)·γ     偏离
  B ============================================================================================
  O       s2    -0.1701    0.1493   0.2544       -0.1233        -0.0468
  B 汇总
  O       s3    -0.2885    0.1277   0.0239       -0.2467        -0.0418
  B ============================================================================================
  O       s4    -0.3717    0.1750   0.0337       -0.3700        -0.0017
  B   语言                  连续γ        δ_s2       δ_s3       δ_s4     χ²(2)        p
  O   线性约束 Wald 检验 (H0: δ3=2δ2 且 δ4=3δ2)：χ²(2) = 0.113, p = 0.9450
  B   javascript      -0.2288     -0.3112    -0.6409    -0.6529     3.879   0.1437
  O       -> 不能拒绝线性——把序数当等距在本数据上没有暴露问题
  B   java            -0.1233     -0.1701    -0.2885    -0.3717     0.113   0.9450
  O   相对 s1 的变化：s2 -15.6%   s3 -25.1%   s4 -31.0%   单调递减：是
  B 
  O 
  B   拒绝线性的语言：无
  O ============================================================================================
  B   -> 三种语言都不能拒绝线性，§6.1 的连续型口径可以保留；把本表放进 SI 作为'线性假设已检验'的交代即可。
  O 汇总
  B 
  O ============================================================================================
  B 写入 E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\blind\02_estimation\review_r1_reviewer_response_scripts\p1_14_bin_dummies.json
  O   语言                  连续γ        δ_s2       δ_s3       δ_s4     χ²(2)        p
  B 
  O   python          -0.4156     -0.2580    -0.6298    -1.2614     3.675   0.1592
  B 
  O   javascript      -0.2288     -0.3112    -0.6409    -0.6529     3.879   0.1437
  B 
  O   java            -0.1233     -0.1701    -0.2885    -0.3717     0.113   0.9450
  B 
  = 
  O   拒绝线性的语言：无
  B 
  O   -> 三种语言都不能拒绝线性，§6.1 的连续型口径可以保留；把本表放进 SI 作为'线性假设已检验'的交代即可。
  B 
  = 
  O 写入 E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\orig\02_estimation\review_r1_reviewer_response_scripts\p1_14_bin_dummies.json
  B 
  = 

## phaseA_answer_window.log  (orig 30 lines, blind 30 lines)
  O N total = 5,975;  age range 0..36 months
  B N total = 5,500;  age range 0..36 months
  = 
  = ======================================================================
  = A2 — answer-margin dose-DiD (is_answered) under cohort-age restriction
  = ======================================================================
  = 
  O [age>= 0mo]  N=5,975
  B [age>= 0mo]  N=5,500
  O   score*post = +0.0320 (se 0.0140, p=0.02237)
  B   score*post = +0.0417 (se 0.0128, p=0.001094)
  O   s1 answered 0.438->0.375   s4 answered 0.738->0.761
  B   s1 answered 0.564->0.485   s4 answered 0.741->0.776
  = 
  O [age>= 6mo]  N=4,784
  B [age>= 6mo]  N=4,426
  O   score*post = +0.0271 (se 0.0145, p=0.06226)
  B   score*post = +0.0394 (se 0.0135, p=0.003528)
  O   s1 answered 0.438->0.390   s4 answered 0.738->0.754
  B   s1 answered 0.564->0.495   s4 answered 0.741->0.776
  = 
  O [age>=12mo]  N=3,588
  B [age>=12mo]  N=3,351
  O   score*post = +0.0265 (se 0.0183, p=0.1468)
  B   score*post = +0.0379 (se 0.0156, p=0.01501)
  O   s1 answered 0.438->0.370   s4 answered 0.738->0.744
  B   s1 answered 0.564->0.473   s4 answered 0.741->0.761
  = 
  O [age>=18mo]  N=2,389
  B [age>=18mo]  N=2,250
  O   score*post = +0.0230 (se 0.0144, p=0.1094)
  B   score*post = +0.0525 (se 0.0235, p=0.0255)
  O   s1 answered 0.438->0.388   s4 answered 0.738->0.737
  B   s1 answered 0.564->0.418   s4 answered 0.741->0.741
  = 
  = ======================================================================
  = A2 — same on answer_count (mean answers), age>=12
  = ======================================================================
  O   score*post = +0.0070 (se 0.0315, p=0.8234), N=3,588
  B   score*post = +0.0196 (se 0.0310, p=0.5272), N=3,351
  = 
  O VERDICT (age>=12, is_answered): score*post=+0.0265 p=0.1468 -> DOES NOT clearly survive
  B VERDICT (age>=12, is_answered): score*post=+0.0379 p=0.01501 -> SURVIVES
  = DONE
  = 

## phaseA_composition.log  (orig 35 lines, blind 35 lines)
  = ==========================================================================
  = PHASE A1 — composition-friendly dose-response (3 estimators x 3 languages)
  = ==========================================================================
  = 
  = [python]  n_months=60
  O   PPML fixed-total dose  gamma=-0.3698 (se 0.0510, p=4.108e-13)   => -30.9%/point, s4-s1 -67%
  B   PPML fixed-total dose  gamma=-0.2872 (se 0.0326, p=0)   => -25.0%/point, s4-s1 -58%
  O   OLS log-count dose     gamma=-0.4156 (se 0.0673, p=6.691e-10)   [existing headline]
  B   OLS log-count dose     gamma=-0.3038 (se 0.0379, p=1.07e-15)   [existing headline]
  O   log-ratio(s4/s1) post  beta =-1.2162 (se 0.1217, p=1.647e-23, Newey-West L=6)
  B   log-ratio(s4/s1) post  beta =-0.8935 (se 0.1168, p=2.005e-14, Newey-West L=6)
  = 
  = [javascript]  n_months=60
  =   PPML fixed-total dose  gamma=-0.1940 (se 0.0446, p=1.369e-05)   => -17.6%/point, s4-s1 -44%
  =   OLS log-count dose     gamma=-0.2288 (se 0.0674, p=0.0006901)   [existing headline]
  =   log-ratio(s4/s1) post  beta =-0.6239 (se 0.1711, p=0.0002663, Newey-West L=6)
  = 
  = [java]  n_months=60
  =   PPML fixed-total dose  gamma=-0.1237 (se 0.0367, p=0.0007564)   => -11.6%/point, s4-s1 -31%
  =   OLS log-count dose     gamma=-0.1233 (se 0.0524, p=0.01849)   [existing headline]
  =   log-ratio(s4/s1) post  beta =-0.3623 (se 0.1492, p=0.01515, Newey-West L=6)
  = 
  = ==========================================================================
  = PHASE A4 — placebo cutoffs + permutation null (python, headline)
  = ==========================================================================
  O   placebo: true 2022-12 gamma=-0.4156; rank 1/13 most-negative among 13 candidate cutoffs (1 = most extreme)
  B   placebo: true 2022-12 gamma=-0.3038; rank 1/13 most-negative among 13 candidate cutoffs (1 = most extreme)
  O   permutation null (2000 draws, shuffle bin scores): obs gamma=-0.4156, null mean=-0.0052 sd=0.2440, one-sided p=0.04248
  B   permutation null (2000 draws, shuffle bin scores): obs gamma=-0.3038, null mean=-0.0035 sd=0.1770, one-sided p=0.04248
  = 
  = ==========================================================================
  = PHASE A4 — Benjamini-Hochberg FDR across confirmatory family
  = ==========================================================================
  O   python dose (PPML)         raw p=4.108e-13   BH-adj q=1.643e-12
  B   python dose (PPML)         raw p=0   BH-adj q=0
  =   javascript dose (PPML)     raw p=1.369e-05   BH-adj q=2.738e-05
  =   java dose (PPML)           raw p=0.0007564   BH-adj q=0.001008
  =   answer-margin DiD          raw p=0.022   BH-adj q=0.022
  = 
  = DONE
  = 

## run_within_so_llm.log  (orig 89 lines, blind 89 lines)
  = ========================================================================
  = P9 Leg B — RIGOROUS within-SO: dose-response on LLM substitutability
  = ========================================================================
  = panel: bins s1-s4 × 60 months (240 obs)  event=2022-12
  = months: 2021-06..2026-05   clusters (month) = 60
  = 
  = === [0] DESCRIPTIVES (pre vs post ChatGPT) ===
  O   gen_share : pre 0.626  post 0.470  Δ -0.155
  B   gen_share : pre 0.551  post 0.403  Δ -0.148
  O   mean score: pre 2.724  post 2.357  Δ -0.367
  B   mean score: pre 2.437  post 2.022  Δ -0.416
  O   s1 per-mo: pre  15.1  post  24.1  Δ  +9.0
  B   s1 per-mo: pre  23.1  post  31.7  Δ  +8.7
  O   s2 per-mo: pre  21.9  post  28.5  Δ  +6.6
  B   s2 per-mo: pre  16.4  post  18.4  Δ  +2.0
  O   s3 per-mo: pre  36.7  post  33.5  Δ  -3.2
  B   s3 per-mo: pre  32.6  post  27.5  Δ  -5.0
  O   s4 per-mo: pre  25.8  post  13.6  Δ -12.3
  B   s4 per-mo: pre  22.6  post  12.8  Δ  -9.8
  = 
  = === [1] DOSE-RESPONSE DiD (headline; γ = score×post, month-clustered) ===
  O   γ = -0.4156  SE 0.0673  t -6.17  p 0.0000
  B   γ = -0.3038  SE 0.0379  t -8.02  p 0.0000
  O   → each +1 substitutability point ⇒ -34.0% on log-count post-ChatGPT
  B   → each +1 substitutability point ⇒ -26.2% on log-count post-ChatGPT
  O   → s4-vs-s1 differential post = -71.3% (3 score points apart)
  B   → s4-vs-s1 differential post = -59.8% (3 score points apart)
  = 
  = === [2] GEN vs VER binary DiD (compare to tag probe) ===
  O   β = -0.6433  SE 0.1209  p 0.0000  → GEN vs VER post -47.4%
  B   β = -0.6100  SE 0.1031  p 0.0000  → GEN vs VER post -45.7%
  = 
  = === [3] EVENT STUDY (dose slope γ_k by event time; k=-1 ref) ===
  =      k   gamma_k
  O    -18   -0.4001  PRE
  B    -18   -0.2384  PRE
  O    -17   -0.4234  PRE
  B    -17   -0.1602  PRE
  O    -16   +0.0229  PRE
  B    -16   -0.0725  PRE
  O    -15   -0.3867  PRE
  B    -15   -0.0235  PRE
  O    -14   -0.2297  PRE
  B    -14   +0.0625  PRE
  O    -13   -0.5954  PRE
  B    -13   -0.1518  PRE
  O    -12   +0.0368  PRE
  B    -12   +0.0322  PRE
  O    -11   -0.6795  PRE
  B    -11   -0.2375  PRE
  O    -10   -0.3833  PRE
  B    -10   -0.1217  PRE
  O     -9   -0.3677  PRE
  B     -9   -0.1423  PRE
  O     -8   -0.4707  PRE
  B     -8   -0.3194  PRE
  O     -7   -0.1937  PRE
  B     -7   -0.2749  PRE
  O     -6   -0.3216  PRE
  B     -6   -0.0864  PRE
  O     -5   -0.3117  PRE
  B     -5   -0.1958  PRE
  O     -4   -0.5326  PRE
  B     -4   -0.1237  PRE
  O     -3   -0.1869  PRE
  B     -3   -0.1040  PRE
  O     -2   -0.4788  PRE
  B     -2   -0.1014  PRE
  O     +0   -0.7089  post
  B     +0   -0.0605  post
  O     +1   -0.6733  post
  B     +1   -0.1957  post
  O     +2   -0.2096  post
  B     +2   -0.1211  post
  O     +3   -0.3486  post
  B     +3   -0.3039  post
  O     +4   -1.1219  post
  B     +4   -0.4846  post
  O     +5   -0.5341  post
  B     +5   -0.2643  post
  O     +6   -0.5910  post
  B     +6   -0.2985  post
  O     +7   -0.4140  post
  B     +7   -0.3193  post
  O     +8   -0.9670  post
  B     +8   -0.6050  post
  O     +9   -0.8494  post
  B     +9   -0.4611  post
  O    +10   -0.6577  post
  B    +10   -0.3312  post
  O    +11   -0.6096  post
  B    +11   -0.3757  post
  O    +12   -0.5944  post
  B    +12   -0.5713  post
  O    +13   -0.8659  post
  B    +13   -0.4024  post
  O    +14   -0.5842  post
  B    +14   -0.3228  post
  O    +15   -0.8797  post
  B    +15   -0.6338  post
  O    +16   -0.7300  post
  B    +16   -0.6336  post
  O    +17   -0.7015  post
  B    +17   -0.6015  post
  O    +18   -0.8441  post
  B    +18   -0.6060  post
  O    +19   -0.8369  post
  B    +19   -0.4765  post
  O    +20   -1.3400  post
  B    +20   -0.6142  post
  O    +21   -0.7954  post
  B    +21   -0.3627  post
  O    +22   -0.7369  post
  B    +22   -0.4294  post
  O    +23   -1.0152  post
  B    +23   -0.4900  post
  O    +24   -0.8987  post
  B    +24   -0.4947  post
  O    +25   -0.9140  post
  B    +25   -0.7396  post
  O    +26   -0.7980  post
  B    +26   -0.4895  post
  O    +27   -0.6055  post
  B    +27   -0.4554  post
  O    +28   -0.7256  post
  B    +28   -0.3062  post
  O    +29   -0.6215  post
  B    +29   -0.4833  post
  O    +30   -0.6077  post
  B    +30   -0.3839  post
  O    +31   -0.8327  post
  B    +31   -0.3972  post
  O    +32   -0.9116  post
  B    +32   -0.6083  post
  O    +33   -0.6527  post
  B    +33   -0.4268  post
  O    +34   -0.7648  post
  B    +34   -0.4653  post
  O    +35   -0.9691  post
  B    +35   -0.3754  post
  O    +36   -1.0116  post
  B    +36   -0.4654  post
  O    +37   -1.0358  post
  B    +37   -0.3914  post
  O    +38   -0.7052  post
  B    +38   -0.3527  post
  O    +39   -0.5658  post
  B    +39   -0.3285  post
  O    +40   -0.5066  post
  B    +40   -0.3431  post
  O    +41   -0.4907  post
  B    +41   -0.5593  post
  = 
  O   pre dose-slope trend: intercept -0.3912, slope -0.00441/mo  (≈flat)
  B   pre dose-slope trend: intercept -0.1636, slope -0.00307/mo  (≈flat)
  O   honest detrended mean post dose-γ = -0.2619 (raw mean post dose-γ -0.7435)
  B   honest detrended mean post dose-γ = -0.2028 (raw mean post dose-γ -0.4293)
  = 
  O [saved] E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\orig\data\within_so_llm_eventstudy.csv
  B [saved] E:\智能体论文\P9b_IPM_20260919\工作文档\R2_downstream\blind\data\within_so_llm_eventstudy.csv
  = 

## s17_bound_both_samples.log  (orig 9 lines, blind 1 lines)
  O Sample of 5,640 (final three months dropped) questions
  B 
  O   closure tracer, 95% upper bound on migrant fraction: s1 15.7%, s2 13.1%
  B 
  O   answer tracer,  95% upper bound on migrant fraction: s1 2.4%, s2 2.0%
  B 
  O   share of the gain the answer tracer leaves to relabelling: s1 6%, s2 9%
  B 
  O Sample of 5,930 (final three months kept) questions
  B 
  O   closure tracer, 95% upper bound on migrant fraction: s1 19.0%, s2 22.7%
  B 
  O   answer tracer,  95% upper bound on migrant fraction: s1 -20.8%, s2 -24.3%
  B 
  O   share of the gain the answer tracer leaves to relabelling: s1 0%, s2 0%
  B 
  = 

## s17_length_conditioned.log  (orig 20 lines, blind 20 lines)
  = === A. length-conditioned tracers in the receiving bins ===
  =   'long' = above the PRE-period median length of that bin (fixed cut)
  O   s1 long  dup≤90d  : pre 0.015 (N=135)  post 0.013 (N=595)  diff -0.001 [-0.024, +0.021]
  B   s1 long  dup≤90d  : pre 0.029 (N=206)  post 0.019 (N=794)  diff -0.010 [-0.035, +0.015]
  O   s1 long  answers  : pre 0.874 (N=135)  post 0.763 (N=595)  diff -0.111 [-0.282, +0.060]
  B   s1 long  answers  : pre 1.049 (N=206)  post 0.898 (N=794)  diff -0.151 [-0.289, -0.013]
  O       reference, long-s4 pre: dup 0.104  answers 1.494  (N=231)
  B       reference, long-s4 pre: dup 0.114  answers 1.490  (N=202)
  O   s2 long  dup≤90d  : pre 0.036 (N=196)  post 0.028 (N=717)  diff -0.008 [-0.036, +0.021]
  B   s2 long  dup≤90d  : pre 0.034 (N=145)  post 0.016 (N=451)  diff -0.019 [-0.051, +0.013]
  O   s2 long  answers  : pre 0.964 (N=196)  post 0.886 (N=717)  diff -0.079 [-0.189, +0.032]
  B   s2 long  answers  : pre 1.021 (N=145)  post 0.978 (N=451)  diff -0.043 [-0.189, +0.103]
  O       reference, long-s4 pre: dup 0.104  answers 1.494  (N=231)
  B       reference, long-s4 pre: dup 0.114  answers 1.490  (N=202)
  = 
  = === B. does length itself predict the tracers, within bin, pre-period? ===
  =   (if length has little tracer effect, S17's attenuation worry is small)
  O   dup           ~ log(length) | bin FE :  -0.0461 (SE 0.0113, p=0.000)
  B   dup           ~ log(length) | bin FE :  -0.0528 (SE 0.0120, p=0.000)
  O   answer_count  ~ log(length) | bin FE :  -0.0558 (SE 0.0412, p=0.175)
  B   answer_count  ~ log(length) | bin FE :  -0.1014 (SE 0.0440, p=0.021)
  = 
  = === C. tracer gradient with length controlled (post only) ===
  O   dup          : s slope +0.0217 -> with length +0.0201
  B   dup          : s slope +0.0264 -> with length +0.0247
  O   answer_count : s slope +0.2424 -> with length +0.2333
  B   answer_count : s slope +0.1716 -> with length +0.1613
  = 
  = written: s17_length_conditioned.json
  = 
