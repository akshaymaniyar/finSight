"""
Default two-level category hierarchy.

Inspired by Splitwise's structure, adapted for Indian personal finance.
Categories are seeded as system defaults (user_id=NULL).
"""

from __future__ import annotations

# (name, icon, color, is_income, [(subcategory_name, keywords), ...])
DEFAULT_CATEGORIES = [
    ("Food & Dining", "utensils", "#FF6B6B", False, [
        ("Groceries", "bigbasket,blinkit,zepto,instamart,jiomart,dmart,dunzo,grocery,supermarket,fresh,vegetables,fruits,more supermarket,spencers,nature basket"),
        ("Dining Out", "restaurant,dineout,eatsure,barbeque nation,haldiram,punjab grill,biryani,cafe,dhaba"),
        ("Food Delivery", "swiggy,zomato,eatsure,faasos,behrouz,eatfit,dominos,pizza hut,mcdonalds,burger king,kfc,subway"),
        ("Cafe & Drinks", "starbucks,cafe coffee day,ccd,chaayos,third wave,blue tokai,tea,coffee"),
        ("Alcohol", "liquor,wine,beer,bar,pub,brewery"),
        ("Other", "food,snack,bakery,sweet"),
    ]),
    ("Shopping", "shopping-bag", "#4ECDC4", False, [
        ("Online Shopping", "amazon,flipkart,meesho,tata cliq,snapdeal,shoppers stop"),
        ("Fashion & Clothing", "myntra,ajio,h&m,zara,uniqlo,lifestyle,pantaloons,westside,nykaa fashion,clothing,fashion"),
        ("Electronics", "croma,vijay sales,reliance digital,apple store,samsung,electronics"),
        ("Home & Furniture", "ikea,pepperfry,urban ladder,home centre,furniture,home decor"),
        ("Beauty & Personal Care", "nykaa,purplle,beauty,cosmetics,skincare,salon product"),
        ("Sports & Fitness", "decathlon,sports,fitness,gym equipment"),
        ("Other", "shopping,mall,mart,retail"),
    ]),
    ("Housing", "home", "#45B7D1", False, [
        ("Rent", "rent,house rent,flat rent,pg rent,nobroker,magicbricks,99acres"),
        ("Society Maintenance", "society maintenance,hoa,association,maintenance charge"),
        ("Home Loan EMI", "home loan,housing loan,mortgage"),
        ("Home Insurance", "home insurance,property insurance"),
        ("Repairs & Maintenance", "plumber,electrician,carpenter,repair,maintenance,painting"),
        ("Other", "housing,home"),
    ]),
    ("Transportation", "car", "#96CEB4", False, [
        ("Cab / Ride", "uber,ola,rapido,cab,ride,taxi,auto rickshaw"),
        ("Fuel", "petrol,diesel,fuel,indian oil,hp ,bpcl,shell,iocl"),
        ("Public Transport", "metro,bus,train,irctc,local train"),
        ("Flight", "indigo,spicejet,air india,vistara,akasa,makemytrip,goibibo,cleartrip,yatra,flight"),
        ("Parking & Toll", "parking,toll,fastag"),
        ("Vehicle Maintenance", "service,tyre,tire,car wash,car repair,mechanic"),
        ("Vehicle EMI", "car loan,vehicle loan,auto loan"),
        ("Other", "transport,travel"),
    ]),
    ("Bills & Utilities", "zap", "#FFEAA7", False, [
        ("Electricity", "electricity,bescom,msedcl,tata power,reliance energy,torrent power"),
        ("Mobile & Internet", "airtel,jio,vi ,vodafone,bsnl,broadband,wifi,internet,mobile bill,recharge,postpaid,prepaid"),
        ("Gas", "piped gas,lpg,adani gas,mahanagar gas,indane,hp gas"),
        ("Water", "water bill,bwssb,water supply"),
        ("DTH & Cable", "tata sky,tata play,dish tv,d2h,airtel xstream,cable tv"),
        ("Other", "utility,bill"),
    ]),
    ("Entertainment", "film", "#DDA0DD", False, [
        ("Movies & Shows", "bookmyshow,pvr,inox,cinepolis,movie,cinema"),
        ("Streaming", "netflix,amazon prime,hotstar,disney,zee5,sonyliv,jiocinema"),
        ("Music", "spotify,gaana,apple music,youtube music"),
        ("Gaming", "playstation,xbox,steam,epic games,gaming"),
        ("Outings & Events", "event,concert,show,exhibition,amusement,theme park"),
        ("Other", "entertainment"),
    ]),
    ("Health & Wellness", "heart", "#FF8A80", False, [
        ("Doctor & Consultation", "doctor,consultation,practo,clinic,hospital,specialist,dermatologist,dentist"),
        ("Pharmacy", "pharmacy,medical,apollo pharmacy,medplus,netmeds,pharmeasy,1mg,tata 1mg,medicine"),
        ("Lab & Diagnostics", "diagnostic,lab,pathology,lalpath,thyrocare,metropolis,test"),
        ("Gym & Fitness", "gym,cult.fit,cultfit,fitness,yoga,workout"),
        ("Mental Health", "therapy,counseling,mental health,psychologist"),
        ("Other", "health,wellness,ayurveda"),
    ]),
    ("Education", "book-open", "#81D4FA", False, [
        ("School & College Fees", "school,college,university,tuition,education fee"),
        ("Online Courses", "udemy,coursera,unacademy,byju,upgrad,simplilearn,skillshare"),
        ("Books & Stationery", "books,stationery,kindle,amazon kindle,library"),
        ("Coaching & Tuition", "coaching,tuition,tutorial,classes"),
        ("Other", "education,learning,exam"),
    ]),
    ("Insurance", "shield", "#A5D6A7", False, [
        ("Health Insurance", "health insurance,star health,care health,niva bupa,max bupa"),
        ("Life Insurance", "lic,max life,hdfc life,icici prudential,sbi life,tata aia,life insurance"),
        ("Vehicle Insurance", "car insurance,bike insurance,motor insurance,vehicle insurance"),
        ("Term Insurance", "term insurance,term plan"),
        ("Other", "insurance,premium,policy,policybazaar,acko"),
    ]),
    ("EMI & Loans", "credit-card", "#FFB74D", False, [
        ("Credit Card EMI", "emi,credit card emi,cc emi"),
        ("Personal Loan", "personal loan,loan repayment"),
        ("Education Loan", "education loan,student loan"),
        ("Other", "loan,emi,equated monthly,bajaj finserv,home credit"),
    ]),
    ("Investments", "trending-up", "#66BB6A", False, [
        ("Mutual Funds", "sip,groww,kuvera,coin,mf purchase,mutual fund,nippon,hdfc mf,icici pru,aditya birla,dsp,kotak mf,axis mf,tata mf,parag parikh"),
        ("Stocks & Trading", "zerodha,upstox,groww,angel one,angel broking,smallcase,stocks,trading"),
        ("Fixed Deposits", "fd ,fixed deposit,recurring deposit,rd "),
        ("PPF & NPS", "ppf,nps,provident fund,pension"),
        ("Gold & Others", "gold,sovereign gold,sgb,digital gold"),
        ("Other", "investment,invest"),
    ]),
    ("Subscriptions", "repeat", "#CE93D8", False, [
        ("App Subscriptions", "subscription,membership,chatgpt,github,linkedin premium,notion,dropbox"),
        ("Cloud Storage", "google storage,icloud,onedrive,cloud"),
        ("News & Magazines", "magazine,newspaper,news,times,kindle unlimited"),
        ("Other", "subscription,recurring,renewal,annual fee"),
    ]),
    ("Family & Social", "users", "#F48FB1", False, [
        ("Gifts", "gift,present,birthday,anniversary"),
        ("Festivals & Celebrations", "diwali,holi,eid,christmas,festival,celebration,puja"),
        ("Weddings & Functions", "wedding,function,shaadi,marriage"),
        ("Donations & Charity", "donation,charity,ngo,temple,church,mosque,gurudwara"),
        ("Other", "family,social"),
    ]),
    ("Domestic Help", "briefcase", "#BCAAA4", False, [
        ("Maid / Cook", "maid,cook,domestic help,house help"),
        ("Driver", "driver,chauffeur"),
        ("Other Services", "washerman,dhobi,gardener,watchman,security"),
        ("Other", "domestic"),
    ]),
    ("Children", "baby", "#80DEEA", False, [
        ("School & Activities", "school fee,activity,class,sport,camp"),
        ("Baby & Kids Supplies", "baby,diaper,formula,toy,firstcry,hopscotch"),
        ("Daycare", "daycare,creche,nanny,babysitter"),
        ("Other", "child,kid"),
    ]),
    ("ATM & Cash", "banknote", "#B0BEC5", False, [
        ("ATM Withdrawal", "atm,cash withdrawal,atm withdrawal,cash wdl,nfs withdrawal"),
        ("Cash Deposit", "cash deposit"),
        ("Other", "cash"),
    ]),
    # --- Income categories ---
    ("Salary & Income", "wallet", "#4CAF50", True, [
        ("Salary", "salary,payroll,stipend"),
        ("Freelance", "freelance,consulting,contract"),
        ("Business Income", "business,revenue,invoice"),
        ("Rental Income", "rental income,rent received"),
        ("Other", "income"),
    ]),
    ("Investment Returns", "bar-chart", "#26A69A", True, [
        ("Dividends", "dividend"),
        ("Interest", "interest credited,credit interest,fd interest,savings interest"),
        ("Capital Gains", "capital gain,stock sale,mf redemption"),
        ("Other", "return,payout"),
    ]),
    ("Refunds & Cashback", "rotate-ccw", "#78909C", True, [
        ("Refund", "refund,reversal,returned"),
        ("Cashback", "cashback,reward,cashback reward"),
        ("CC Bill Payment", "cc payment,credit card payment,cc bill,card bill payment,billpay,bill payment,bppy cc payment,cc pymt,payment received,autopay"),
        ("Other", "credit"),
    ]),
    ("Transfers", "arrow-left-right", "#90A4AE", False, [
        ("Self Transfer", "self,own account,self transfer,neft-self,imps-self,upi-self"),
        ("Transfer to Family", "transfer,sent to"),
        ("Other", "transfer"),
    ]),
    ("Uncategorized", "help-circle", "#9E9E9E", False, [
        ("General", ""),
    ]),
]
