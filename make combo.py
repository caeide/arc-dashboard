import pandas as pd

# to combine all static loads
alma = pd.read_csv('data/alma_arc.csv', dtype={'Barcode': 'string'})
alma = alma[alma['Barcode'].str.contains(r'(^[0-9]+$)', regex=True)]
alma['Pub Decade'] = alma['Publication Date'].str.extract(r'(\d{3})') + '0'
alma['Pub Decade'] = alma['Pub Decade'].fillna(0)
alma = alma.astype({'Barcode': 'int64', 'Pub Decade': 'int64'})

dematic_items = pd.read_csv('data/inventory all 03112020.csv',
                            usecols=['Item Number', 'Circulation Status', 'Container ID', 'Audit Date', 'Store Date',
                                     'Storage Type'],
                            parse_dates=['Audit Date', 'Store Date'],
                            date_format='%m/%d/%Y %I:%M:%S %p', dtype={'Item Number': 'string'})
dematic_items = dematic_items[dematic_items['Item Number'].str.contains(r'(^[0-9]+$)', regex=True)]
dematic_items = dematic_items.astype({'Item Number': 'int64'})

dematic_bins = pd.read_csv('data/all bins  03112020.csv', parse_dates=['Audit Date'],
                           date_format='%m/%d/%Y %I:%M:%S %p',
                           usecols=['Container ID', 'Audit Date', 'Restricted Access'])
dematic_bins = dematic_bins.rename(columns={'Audit Date': 'Bin Audit Date'})

combo_items = pd.merge(dematic_items, alma, how='left', left_on='Item Number', right_on='Barcode')
combo = pd.merge(combo_items, dematic_bins, how='left', on='Container ID')

# remove archives items, drop un-needed columns
combo = combo.drop(combo[combo['Restricted Access'] == 'Y'].index)
combo = combo.drop(['Barcode', 'Restricted Access'], axis=1)


# assign correct original store year
def assign_date(x, y, z):
   if x is not pd.NaT:
       return x
   else:
       if y is not pd.NaT:
           return y
       else:
           if z is not pd.NaT:
               return z
           else:
               return '1998-02-17 20:30:00'


combo['Store Year'] = combo.apply(lambda row: assign_date(row['Store Date'], row['Bin Audit Date'], row['Audit Date']),
                                  axis=1)
combo['Store Year'] = pd.DatetimeIndex(combo['Store Year']).year

# parse location info
combo['aisle'] = combo['Container ID'].str.slice(start=2, stop=4) + combo['Container ID'].str.slice(start=-2)
combo['bay'] = combo['Container ID'].str.slice(start=4, stop=7)
combo['level'] = combo['Container ID'].str.slice(start=7, stop=9)


# create spacing for legible graphs later
def get_aisle(aisle):
    if aisle == '0121':
        return 0
    elif aisle == '0111':
        return 30
    elif aisle == '0221':
        return 60
    elif aisle == '0211':
        return 90
    elif aisle == '0321':
        return 120
    elif aisle == '0311':
        return 150
    else:
        pass


combo['fake aisle'] = combo['aisle'].apply(get_aisle)
combo = combo.astype({'bay': 'float64', 'level': 'float64', 'fake aisle': 'float64'})

combo.to_csv('combo.csv', index=False)