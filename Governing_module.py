from bs4 import BeautifulSoup
from Topic_collection_module import TopicCollection
from Lookup_module import ArrangeDatabase, ConvertWorkbook, GeneralTemplates, GameCourseTemplates, GameStatisticsTemplates
from Template_selection_module import GeneralTemplateSelection, GameCourseTemplateSelection, GameStatisticsTemplateSelection
from Template_filler_module import TemplateReplacement
from Text_collection_module import TextCollection
import pickle

def GeneralEvents():
    #General events in the current system consist of three sentences: a title, a general sentence describing whether the focus team won/tied/lost,
    #A general sentence detailing the final score.
    return ['title', 'general', 'final_score']

def TopicWalk(file):
    topics = TopicCollection(file)
    #Get three lists for the three paragraphs the current system uses: General, Game Course and Game Statistics
    general, gamecourse, gamestatistics = (GeneralEvents(),) + topics
    if len(gamestatistics) == 0:
        gamestatistics = [{'event': None}]

    # Get the right databases for the home and away report
    homedbtuple, awaydbtuple = ArrangeDatabase(file)
    # Get all the templates and categories
    homelegend, hometemplates = ConvertWorkbook(homedbtuple[0])
    awaylegend, awaytemplates = ConvertWorkbook(awaydbtuple[0])

    # The soup is important for many rules in the RuleSet
    with open(file, 'rb') as f:
        soup = BeautifulSoup(f, "lxml")

    # Collect all the home and away templates
    templatehomelist = []
    templateawaylist = []
    #Get all possible topics for general first
    for generaltopic in general:
        possiblelegendhome, possibletemplateshome, possiblelegendaway, possibletemplatesaway = GeneralTemplates(generaltopic, homelegend, hometemplates, awaylegend, awaytemplates)
        #Select a template for the home team
        templatehome = GeneralTemplateSelection(generaltopic, possiblelegendhome, possibletemplateshome, gamecourse, gamestatistics, soup, 'home')
        templatehomelist.append(templatehome)
        #And a template for the away team
        templateaway = GeneralTemplateSelection(generaltopic, possiblelegendaway, possibletemplatesaway, gamecourse, gamestatistics, soup, 'away')
        templateawaylist.append(templateaway)

    #Get a separate gamecoursehome and away, since the gamecourselist can be modified
    gamecoursehome = gamecourse.copy()
    gamecourseaway = gamecourse.copy()

    # And then for the gamecourse
    for idx, gamecoursetopic in enumerate(gamecourse):
        #The subsequent goals template merges events and shortens the gamecourse, so only look for a template if there is the need for it in the gamecourselist
        if idx < len(gamecoursehome):
            possiblelegendhome, possibletemplateshome, possiblelegendaway, possibletemplatesaway = GameCourseTemplates(gamecoursehome[idx], homelegend, hometemplates, awaylegend, awaytemplates)
            gamecoursehome, templatehome = GameCourseTemplateSelection(gamecoursehome[idx], possiblelegendhome, possibletemplateshome, gamecoursehome, soup, 'home', idx, templatehomelist)
            templatehomelist.append(templatehome)
        if idx < len(gamecourseaway):
            possiblelegendhome, possibletemplateshome, possiblelegendaway, possibletemplatesaway = GameCourseTemplates(gamecourseaway[idx], homelegend, hometemplates, awaylegend, awaytemplates)
            gamecourseaway, templateaway = GameCourseTemplateSelection(gamecourseaway[idx], possiblelegendaway, possibletemplatesaway, gamecourseaway, soup, 'away', idx, templateawaylist)
            templateawaylist.append(templateaway)
    #And then for the game statistics
    for idx, gamestatisticstopic in enumerate(gamestatistics):
        #If this is not the first yellow card/twice yellow card in the list, than the event is already covered and altered by the previous event
        #So, if the eventtype is not a dict, skip it
        if type(gamestatistics[idx]) == dict:
            possiblelegendhome, possibletemplateshome, possiblelegendaway, possibletemplatesaway = GameStatisticsTemplates(gamestatisticstopic, homelegend, hometemplates, awaylegend, awaytemplates)
            templatehome = GameStatisticsTemplateSelection(gamestatistics[idx], possiblelegendhome, possibletemplateshome, gamestatistics, soup, 'home', idx, templatehomelist)
            templatehomelist.append(templatehome)
            templateaway = GameStatisticsTemplateSelection(gamestatistics[idx], possiblelegendaway, possibletemplatesaway, gamestatistics, soup, 'away', idx, templateawaylist)
            templateawaylist.append(templateaway)

    # Save the templatelist, which you can use to get new templates every iteration
    with open('templateshome.p', 'wb') as f:
        pickle.dump(templatehomelist, f)
    with open('templatesaway.p', 'wb') as f:
        pickle.dump(templateawaylist, f)

    #Filter out all the empty strings from gamestatistics
    gamestatistics = list(filter(None, gamestatistics))
    alleventshome = general + gamecoursehome + gamestatistics
    alleventsaway = general + gamecourseaway + gamestatistics
    previousgaplisthome = [''] * len(templatehomelist)
    for idx, val in enumerate(templatehomelist):
        if idx <= 1:
            lastgaphome = []
        else:
            lastgaphome = previousgaplisthome[idx - 1]
        templatehomelist[idx], previousgaplisthome[idx] = TemplateReplacement(soup, 'home', templatehomelist[idx], event=alleventshome[idx], gamecourselist=gamecoursehome, previousgaplist=lastgaphome, gamestatisticslist=gamestatistics, eventlist=alleventshome, idx=idx)
    templatetexthome, templatedicthome = TextCollection(templatehomelist, soup, 'home', len(general), len(gamecoursehome), len(gamestatistics))

    previousgaplistaway = [''] * len(templateawaylist)
    for idx, val in enumerate(templateawaylist):
        if idx <= 1:
            lastgapaway = []
        else:
            lastgapaway = previousgaplistaway[idx - 1]
        templateawaylist[idx], previousgaplistaway[idx] = TemplateReplacement(soup, 'away', templateawaylist[idx], event=alleventsaway[idx],
                                                                          gamecourselist=gamecourseaway, previousgaplist=lastgapaway,
                                                                          gamestatisticslist=gamestatistics, eventlist=alleventsaway, idx=idx)
    templatetextaway, templatedictaway = TextCollection(templateawaylist, soup, 'away', len(general), len(gamecourseaway), len(gamestatistics))
    templatedict = templatedicthome.copy()
    templatedict.update(templatedictaway)
    return templatetexthome, templatetextaway, templatedict