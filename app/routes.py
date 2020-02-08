from app import app
from app.settings import MYSQL_SERVER, MYSQL_USER, MYSQL_PASS, MYSQL_DB, MYSQL_PORT
from flask import Response, request, render_template
import datetime
import mysql.connector
import json

days = {
  'sv': [' ', u'Måndag', u'Tisdag', u'Onsdag', u'Torsdag', u'Fredag', u'Lördag', u'Söndag']
  'en': [' ', u'Monday', u'Tuesday', u'Wednesday', u'Thursday', u'Friday', u'Saturday', u'Sunday']
  'fi': [' ', u'Maanantai', u'Tiistai', u'Keskiviikko', u'Torstai', u'Perjantai', u'Lauantai', u'Sunnuntai']
}

#Funktionen som söker menyn från databasen
def mySQL(language, day, month, year):
  connection = mysql.connector.connect(host=MYSQL_SERVER, port=MYSQL_PORT, user=MYSQL_USER, passwd=MYSQL_PASS, db=MYSQL_DB)
  cursor = connection.cursor()

  if language == 'sv':
    lang_table = 'namn_swe';
  elif language == 'fi':
    lang_table = 'namn_fi'
  else:
    lang_table = 'namn_eng'

  SQL = """
SELECT DISTINCT CONCAT(IF(B.matratts_typ=2,'A la Carte: ',''),B.%s,' ',IFNULL(specialdiet,'')) AS namn FROM tbl_dagens_meny AS A,tbl_matratts_lista AS B LEFT 
JOIN (SELECT matratts_id,CONCAT('(', GROUP_CONCAT(forkortning SEPARATOR ', '), ')') AS specialdiet 
FROM tbl_specialdieter AS A,tbl_diettyper AS B 
WHERE A.specialdiet=B.specialdiets_id AND B.hemsidan=1 
GROUP BY matratts_id) AS C USING(matratts_id),tbl_matratts_typ AS D 
WHERE A.matratts_id=B.matratts_id AND B.matratts_typ=D.matratts_typ_id AND datum=%s ORDER BY sort_order;
""" % (lang_table, '%s')

  cursor.execute(SQL, (datetime.date(year, month, day), ))
  result = cursor.fetchall()
  
  cursor.close()
  connection.close()
  return result

#APIns framsida
@app.route('/')
@app.route('/taffa/')
def index():
  return render_template('Dagsen/index.html', hostname=request.host)
  
#Metametod för default meny
@app.route('/taffa/<language>/<day>/<month>/<year>/')
def defaultMenu(language, day, month, year):
  return textMenu(language, day, month, year)

@app.route('/taffa/<language>/txt/<day>/<month>/<year>/')
def textMenu(language, day, month, year):
  menu = mySQL(language, int(day), int(month), int(year))
  output = ""

  if len(menu) == 0:
    output = "No menu available"

  for line in menu:
    output += "%s\r\n" % line[0]

  return Response(output, mimetype="text/plain; charset=utf-8")
  
@app.route('/taffa/<language>/today/')
def textToday(language):
  #date = datetime.date.today()
  return textPlusMeals(language, 0)

#Returnerar den N:nte nästa menyn (0=idag, 1=imorgon osv.)
# N max = 5 (lördag och söndag visas inte)
@app.route('/taffa/<language>/<int:days>/')
def textPlusMeals(language, days):
  date = nextMealDate(days) 
  return textMenu(language, date.day, date.month, date.year)

#Returnerar den N:te nästa menyns datum (alltså inte lö-sö)
def nextMealDate(days):
  datum = datetime.date.today()
  datum = datum + datetime.timedelta(hours=-12)
  d = int(days)

  for i in range(0, d+1):
      datum = datum + datetime.timedelta(days=1)
      while (datum.isoweekday() > 5):
        datum = datum + datetime.timedelta(1) 

  return datum

@app.route('/taffa/<language>/json/<day>/<month>/<year>/')
def jsonDateMenu(language, day, month, year):
  date = datetime.date(int(year), int(month), int(day))
  return jsonMenu(language, date)


def jsonMenu(language, date):
  response = json.dumps(jsonDictionary(language, date), ensure_ascii=False, encoding='utf8')
  return Response(response, mimetype='application/json; charset:utf-8')

def jsonDictionary(language, date):
  menu = mySQL(language, int(date.day), int(date.month), int(date.year))
  obj = {}
  obj["day"] = date.isoweekday()
  obj["date"] = "%d.%d.%d" % (date.day, date.month, date.year)

  obj["dayname"] = days[language][date.isoweekday()]

  if len(menu) == 0:
    obj["extra"] = "No menu available"
    return obj
  elif len(menu) == 1:
    obj["extra"] = menu[0][0]
    return obj

  fields = ['main', 'vegetarian','salad','soup','alacarte','extra']

  i = 0
  for field in fields:
    try:
      obj[field] = menu[i][0]
    except:
      obj[field] = ''

    #Dirty hack
    if 'Ei tarjolla' in obj[field] or 'Not available' in obj[field] or 'Serveras ej' in obj[field]:
      obj[field] = ''
    i += 1

  return obj

@app.route('/taffa/<language>/json/<int:days>/')
def jsonNextMeal(language, days):
  date = nextMealDate(days)
  return jsonMenu(language, date)

@app.route('/taffa/<language>/json/today/')
def jsonToday(language):
  today = datetime.date.today()
  return jsonMenu(language, today)

@app.route('/taffa/<language>/json/week/')
def jsonWeek(language):
  week = []
  for i in range(0, 5):
    day = nextMealDate(i)
    week.append(jsonDictionary(language, day))
  response = json.dumps(week)
  return Response(response, mimetype='application/json; charset=utf-8')

@app.route('/taffa/<language>/html/week/')
def htmlWeek(language):
  week = []
  for i in range(0, 5):
    day = nextMealDate(i)
    week.append(jsonDictionary(language, day))

  return render_template("Dagsen/meny.html", week=week)

# TODO: are we supposed to have a route to this?
def txtWeek(language):
  week = []
  for i in range(0, 5):
    day = nextMealDate(i)
    week.append(jsonDictionary(language, day))

  return render_template("Dagsen/meny_txt.html", week=week)

def htmlMenu(language, day):
  week = []
  week.append(jsonDictionary(language, day))
  return render_template("Dagsen/meny.html", week=week)

@app.route('/taffa/<language>/html/today/')
def htmlToday(language):
  return htmlNextMeal(language, 0)

@app.route('/taffa/<language>/html/<day>/<month>/<year>/')
def htmlDateMenu(language, day, month, year):
  day = datetime.date(int(year), int(month), int(day))
  return htmlMenu(language, day)

@app.route('/taffa/<language>/html/<int:days>/')
def htmlNextMeal(language, days):
  date = nextMealDate(days)
  return htmlMenu(language, date)

@app.errorhandler(404)
def not_found(e):
    # note that we set the 404 status explicitly
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    # note that we set the 404 status explicitly
    return render_template('500.html'), 500