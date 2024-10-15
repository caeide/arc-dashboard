from dash import Dash, dcc, html
import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib as mpl
import seaborn as sns
import base64
from io import BytesIO

static = pd.read_csv('combo.csv',
                     dtype={'Item Number': 'int64', 'Pub Decade': 'float64', 'Store Year': 'float64'},
                     usecols=['Item Number', 'Circulation Status', 'Container ID', 'Pub Decade', 'Store Year',
                              'Material Type', 'bay', 'level', 'aisle', 'fake aisle'])

# updating loads
mold_items = pd.read_csv('data/mold items.csv', dtype={'Barcode': 'int64'})
mold_items['Mold Item'] = 'yes'
mold_bins = pd.read_csv('data/reconfigured mold bins.csv',
                        parse_dates=['Audit Date'], date_format='%m/%d/%Y',
                        usecols=['Container ID', 'Number of Mold', 'Audit Date'])
mold_bins = mold_bins.rename(columns={'Audit Date': 'New Audit Date'})

# combine
add_bins = pd.merge(static, mold_bins, how='left', on='Container ID')
combo = pd.merge(add_bins, mold_items, how='left', left_on='Item Number', right_on='Barcode')
combo = combo.drop(['Barcode', 'Number of Mold'], axis=1)

# specify for audited items only
audited_items = combo[combo['New Audit Date'].notnull()].copy()
audited_items['Month'] = pd.DatetimeIndex(audited_items['New Audit Date']).month
audited_items['Year'] = pd.DatetimeIndex(audited_items['New Audit Date']).year
audited_items['Mold or Not'] = np.where(audited_items['Mold Item'].isnull(), 'No', 'Yes')
items_total = audited_items.groupby('Mold or Not').agg({'Item Number': 'count'}).reset_index()

# make groupings for pie charts
mold_items = audited_items.drop(audited_items[audited_items['Mold or Not'] == 'No'].index).copy()
mold_by_decade = mold_items.groupby('Pub Decade').agg({'Item Number': 'count'}).reset_index()
mold_by_type = mold_items.groupby('Material Type').agg({'Item Number': 'count'}).reset_index()
mold_by_store = mold_items.groupby('Store Year').agg({'Item Number': 'count'}).reset_index()
not_mold_items = audited_items.drop(audited_items[audited_items['Mold or Not'] == 'Yes'].index).copy()

# find counts and most common values per container
containers = audited_items.groupby(['Container ID', 'bay', 'aisle', 'level', 'fake aisle']).agg({'Item Number': 'count',
                                    'Mold Item': 'count', 'Pub Decade': pd.Series.mode, 'Store Year': pd.Series.mode,
                                    'Material Type': pd.Series.mode}).reset_index()
containers = pd.merge(containers, mold_bins, how='left', on='Container ID')
containers['Month'] = pd.DatetimeIndex(containers['New Audit Date']).month
containers['Year'] = pd.DatetimeIndex(containers['New Audit Date']).year
containers['Percent Mold'] = containers['Mold Item'] / containers['Item Number']

# find total values
totals = {'total bins': containers['Item Number'].count().item(), 'total items': combo['New Audit Date'].count().item(),
          'total mold items': combo['Mold Item'].count().item()}
fig_table = go.Figure(data=[go.Table(header=dict(values=['Total Bins', 'Total Items', 'Total Mold Items']),
                    cells=dict(values=[containers['Item Number'].count().item(), combo['New Audit Date'].count().item(),
                    combo['Mold Item'].count().item()]))])
table = dcc.Graph(figure=fig_table)

# time to make some charts
percent_pie = px.pie(items_total, values='Item Number', names='Mold or Not', title='Total Items with and without Mold')
percent_pie = dcc.Graph(figure=percent_pie)

# set current to date range to display
current = audited_items[audited_items['Year'] == 2024]
total_items_bar = px.histogram(current, x='Month', y='Item Number', color='Mold or Not', histfunc='count',
                               title='Total Items Audited by Month (2024)')
total_items_bar.update_layout(bargap=0.2)
total_items_bar = dcc.Graph(figure=total_items_bar)

decade_bar = px.histogram(audited_items, x='Pub Decade', y='Item Number', color='Mold or Not', histfunc='count',
                    range_x=[1700, 2100], title='Items by Publication Decade')
decade_bar = decade_bar.update_layout(bargap=0.2)
decade_bar = dcc.Graph(figure=decade_bar)

store_year_bar = px.histogram(audited_items, x='Store Year', y='Item Number', color='Mold or Not', histfunc='count',
                        range_x=[1990, 2030], title='Items by Store Year')
store_year_bar.update_layout(bargap=0.2)
store_year_bar = dcc.Graph(figure=store_year_bar)

material_type_bar = px.histogram(audited_items, x='Material Type', y='Item Number', color='Mold or Not',
                                 histfunc='count', title='Items by Material Type')
material_type_bar.update_layout(bargap=0.2)
material_type_bar = dcc.Graph(figure=material_type_bar)

decade_pie = px.pie(mold_by_decade, values='Item Number', names='Pub Decade', title='Mold Items by Publication Decade')
decade_pie = dcc.Graph(figure=decade_pie)

material_type_pie = px.pie(mold_by_type, values='Item Number', names='Material Type', title='Mold Items by Material Type')
material_type_pie = dcc.Graph(figure=material_type_pie)

store_year_pie = px.pie(mold_by_store, values='Item Number', names='Store Year', title='Mold Items by Store Year')
store_year_pie = dcc.Graph(figure=store_year_pie)

# location graphs
x = -containers['bay']
z = containers['level']
y = containers['fake aisle']

# 3D plot
fig = plt.figure()
ax = fig.add_subplot(projection='3d')
cmap = mpl.colormaps['OrRd']
cmap.set_under('green')
ax.scatter(x, y, z, c=containers['Percent Mold'], cmap=cmap, vmin=.01, vmax=.4)
ax.view_init(azim=-30)
plt.title('Location of Mold (Percent)')
buf = BytesIO()
fig.savefig(buf, format='png')
fig_data = base64.b64encode(buf.getbuffer()).decode('ascii')
fig_3d = f'data:image/png;base64,{fig_data}'

# overlay plot
fig2 = plt.figure()
sns.scatterplot(x='bay', y='level',data=containers, hue='Mold Item', palette='RdYlGn_r', legend=False)
plt.title('Overlay of All Aisles (Number of Mold Items)')
buf2 = BytesIO()
fig2.savefig(buf2, format='png')
fig_data2 = base64.b64encode(buf2.getbuffer()).decode('ascii')
fig_overlay = f'data:image/png;base64,{fig_data2}'

# make the app
app = Dash(__name__)

app.layout = dbc.Container([
    dbc.Row(html.Div(table), className='g-0'),
    dbc.Row([dbc.Col(html.Div(percent_pie), width=6), dbc.Col(html.Div(total_items_bar), width=6)]),
    dbc.Row([dbc.Col(html.Div(decade_bar), width=4), dbc.Col(html.Div(material_type_bar), width=4),
             dbc.Col(html.Div(store_year_bar), width=4)]),
    dbc.Row([dbc.Col(html.Div(decade_pie), width=4), dbc.Col(html.Div(material_type_pie), width=4),
             dbc.Col(html.Div(store_year_pie), width=4)]),
    dbc.Row([dbc.Col(html.Img(src=fig_3d)), dbc.Col(html.Img(src=fig_overlay))])
])
# yes I realize the formatting did not work, but that is the intended display

if __name__=='__main__':
    app.run()