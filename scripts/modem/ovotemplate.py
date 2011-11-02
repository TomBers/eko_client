# -*- coding: cp1252 -*-

# ovotemplate.py
#
# Version 1.0, 1 december 2010
#
# Simple templating class, software by Michiel Overtoom, motoom@xs4all.nl
#
# {=word}  simpele replacement
# {?tag ...} conditional
# {#tag ...} repeat
# {/tag ...} separator
#

import pprint
import re
whitechars = re.compile("\s")

verbose = False
# verbose = True

def indent(level):
    return "| " + "    " * level


class Container(list):
    "Generic container"

    def __init__(self, name=""):
        self.name = name

    def __repr__(self):
        tag = "%s %s" % (self.__class__.__name__, self.name)
        return "%s: %s" % (tag.strip(), super(Container, self).__repr__())

    def render(self, vars, last=False, level=0):
        if verbose: print "%sContainer.render(vars=%s,last=%s) type(vars)=%s, self.name=%s" % (indent(level),vars,last,type(vars),self.name)
        output = ""
        for child in self:
            if verbose: print "%sContainer.render child %s" % (indent(level), child)
            output += child.render(vars, last, level+1)
        return output


class Lit(Container):
    "Container for literal content"

    def __init__(self, contents=""):
        super(Lit, self).__init__()
        self.append(contents)

    def __repr__(self):
        return super(Lit, self).__repr__()

    def render(self, vars, last, level):
        if verbose: print "%sLit.render(vars=%s,last=%s) type(vars)=%s, self=%s" % (indent(level), vars,last,type(vars),self)
        return self[0]


class Sep(Container):
    "Container for separator. Same as Lit, but doesn't result in output in the last iteration of a Rep."

    def __init__(self, name):
        super(Sep, self).__init__(name)

    def __repr__(self):
        return super(Sep, self).__repr__()

    def render(self, vars, last, level):
        if verbose: print "%sSep.render(vars=%s) type(vars)=%s, self=%s" % (indent(level), vars,type(vars),self)
        if last:
            if verbose: print "%sSep.render last is True, empty string returned" % indent(level)
            return ""
        output = ""
        for child in self:
                if verbose: print "%sSep.render child %s" % (indent(level), child)
                output += child.render(vars, last, level+1)
        return output


class Sub(Container):
    "Container for a variable substitution"

    def __init__(self, name):
        super(Sub, self).__init__(name)

    def __repr__(self):
        return super(Sub, self).__repr__()

    def render(self, vars, last, level):
        if verbose: print "%sSub.render(vars=%s) type(vars)=%s, self.name=%s" % (indent(level), vars,type(vars),self.name)
        value = vars[self.name]
        if isinstance(value, (int, float, long)):
            value = str(value)
        return value


class Cond(Container):
    "Container for conditional content"

    def __init__(self, name):
        super(Cond, self).__init__(name)

    def __repr__(self):
        return super(Cond, self).__repr__()

    def render(self, vars, last, level):
        if verbose: print "%sCond.render(vars=%s) type(vars)=%s, self.name=%s" % (indent(level), vars,type(vars),self.name)
        if not vars.get(self.name): # Assume missing template variable is False.
            if verbose: print "%sCond.render cond is False, empty string returned" % indent(level)
            return ""
        output = ""
        for child in self:
                if verbose: print "%sCond.render child %s" % (indent(level), child)
                output += child.render(vars, last, level+1)
        return output


class Rep(Container):
    "Container for repeating content"

    def __init__(self, name):
        super(Rep, self).__init__(name)

    def __repr__(self):
        return super(Rep, self).__repr__()

    def render(self, vars, last, level):
        if verbose: print "%sRep.render(vars=%s) type(vars)=%s, self.name=%s" % (indent(level),vars,type(vars),self.name)
        output = ""
        #if not self.name in vars:
        #    raise NameNotFound("A required variable name '%s' was not present in '%r'" % (self.name, vars))
        subvars = vars[self.name] # A KeyError here means that a required variable wasn't present.
        for nr, subvar in enumerate(subvars):
            if verbose: print "%sRep.render subvar=%s, type(subvar)=%s" % (indent(level),subvar,type(subvar))
            for child in self:
                last = nr == len(subvars)-1
                if verbose: print "%sRep.render child %s, last=%s" % (indent(level), child,last)
                output += child.render(subvar, last, level+1)
        return output


def makecontainer(s):
    "Return a proper container depending on what type is needed"
    # TODO: Wel of niet metachars (?,#,=,/) opnemen in naam?
    name = s[1:].strip()
    if s.startswith("?"):
        tmp = Cond(name)
    elif s.startswith("#"):
        tmp = Rep(name)
    elif s.startswith("="):
        tmp = Sub(name)
    elif s.startswith("/"):
        tmp = Sep(name)
    else:
        # tmp = Lit(name)
        raise ValueError("argument '%s' should begin with =, ?, # or /" % s)
    return tmp


def splitfirst(s):
    "Split a string into a first special word, and the rest"
    if not s:
        return "", ""
    if s[0] in "?#=/":
        parts = whitechars.split(s, 1)
        if len(parts) < 2:
            return s, ""
        else:
            return parts[0], parts[1]
    else:
        return "", s


# level 0 is altijd literal text
# level 1 en hoger is spul dat met { begint
# eerste string moet een van volgende zijn: toegestaan: {?, {#, {=
# de rest van de strings op hetzelfde level is literal text

def descendingparse(s, i=0, level=0):
    "Parse a part of the template recursively"
    if verbose:
        print "%sEnter descendingparse('%s', %d, %d)   s[%d:] = '%s'" % (indent(level), s, i, level, i, s[i:])
    collect = ""
    node = Container() if level == 0 else None
    while i < len(s):
        c = s[i]
        i += 1
        if c == "{":
            if verbose:
                print "%s{ seen on pos %d, collected text in front of it: '%s' " % (indent(level), i-1, collect) # wat voor de { staat
            if level == 0:
                rest = collect
            else:
                first, rest = splitfirst(collect)
                if first:
                    node = makecontainer(first)
            if rest:
                node.append(Lit(rest))
            i, between = descendingparse(s, i, level + 1) # tussen { en }
            node.append(between)
            collect = "" # verzamel opnieuw voor de rest
        elif c == "}":
            if level == 0:
                raise Exception("Too many }")
            if verbose:
                print "%s} seen on pos %d, collected text '%s' output before pop" % (indent(level), i-1, collect) # output before pop
            first, rest = splitfirst(collect)
            if not node:
                node = makecontainer(first)
            if rest:
                node.append(Lit(rest))
            if verbose:
                print "%sLeave descendingparse, return(%d, %r)   s[%d:] = '%s' " % (indent(level), i, node, i, s[i:])
            return i, node # pop
        else:
            collect += c
    # end of input string reached
    if collect:
        if verbose:
            print "%sInput exhausted at pos %d, collected text: '%s' " % (indent(level), i, collect)
        node.append(Lit(collect))
    else:
        if verbose:
            print "%sInput exhausted at pos %d, no collected text" % (indent(level), i)
    if verbose:
        print "%sLeave descendingparse, return(%d, %r)   s[%d:] = '%s' " % (indent(level), i, node, i, s[i:])
    return i, node


class Ovotemplate(object):

    def __init__(self, s=None):
        if s:
            _, self.root = descendingparse(s)
        else:
            self.root = None
            
    def fromfile(self, fn):
        '''
        Allows: tem = Ovotemplate().fromfile("hello.tpl")
        The template file should contain UTF-8 encoded unicode text
        '''
        _, self.root = descendingparse(unicode(open(fn,"rb").read(), "utf-8"))
        return self

    def pprint(self):
        pprint.pprint(self.root)

    def render(self, vars):
        if not self.root:
            raise Exception("You should either pass a template as a string in the constructor, or use 'fromfile' to read the template from file")
        return self.root.render(vars)


if __name__ == "__main__":

    basictests = (
        # Basic tests.
        ("", {}), # pathetisch geval: lege template
        ("a", {}), # een lettertje
        ("hallo daar hoe gaat het ermee?", {}), # langere string
        ("{=status}", {"status": "STATUS"}), # simpele substitutie
        ("{=status}", {"status": 67.2334}),
        ("ERVOOR{=status}", {"status": "STATUS"}),
        ("{=status}ERNA", {"status": "STATUS"}),
        # twee substituties zonder tekst ertussen:
        ("{=one}{=two}", {"one": "ONE", "two": "TWO"}),
        # twee substituties met tekst ertussen:
        ("{=one}AND{=two}", {"one": "ONE", "two": "TWO"}),
        # twee substituties met spatie ertussen:
        ("{=one} {=two}", {"one": "ONE", "two": "TWO"}),
        # twee substituties met spaties ertussen
        ("{=one}    {=two}", {"one": "ONE", "two": "TWO"}),
        # twee substituties met tekst en spatie ertussen
        ("{=one}, {=two}", {"one": "ONE", "two": "TWO"}),
        # twee substituties met spatie en tekst ertussen
        ("{=one} ({=two})", {"one": "ONE", "two": "TWO"}),
        # simpele repetities
        ("{#cls{=co}}", {"cls": ({"co": "red"}, {"co": "gr"}, {"co": "bl"})}),
        ("{#cls <{=co}>}", {"cls": ({"co": "red"}, {"co": "gr"}, {"co": "bl"})}),
        ("{#cls {=co}, }", {"cls": ({"co": "red"}, {"co": "gr"}, {"co": "bl"})}),
        ("{#cls {=co} x }", {"cls": ({"co": "red"}, {"co": "gr"}, {"co": "bl"})}),
        ("{#cls {=co} _}", {"cls": ({"co": "red"}, {"co": "gr"}, {"co": "bl"})}),
        # substitutie met tekst ertussen
        ("well{=here}it{=goes}with{=some}test", {"here": "HERE", "goes": "GOES", "some": "SOME"}),
        # repeat met variabele als laatste op de regel
        ("{#blop\n{=you}\n}", dict(blop=(dict(you=123),dict(you=456)))),
        # simple conditions
        ("throw a {?condition big }party", {"condition": True}),
        ("throw a {?condition big }party", {"condition": False}),
        # repeats
        ("{#a{=b}{=c}}", {"a": ({"b": 11, "c": 22},)}), # the comma behind the } is significant - without it, the dict wouldn't be placed in a tuple.
        ("{#a {=b} {=c}}", {"a": [{"b": 33, "c": 44}]}), # or use a list instead of a tuple
        ("{#a STA{=b}STO  BEG{=c}END }", {"a": ({"b": 55, "c": 66},)}),
        ("{#a {=b} {=c}}", {"a": ({"b": 7.70, "c": 88}, {"b": 99, "c": 1.234567})}),
        ("{#a {=b} {=c}}", {"a": ()}),
        ("{#kleuren {=kleur}{/komma , }}", dict(kleuren=(dict(kleur="rood"),dict(kleur="groen"),dict(kleur="blauw")))),
        # this is an error ("{#a {=b} {=c}}", {}),
        )


    tests = (
        ("buy {=count} articles: {#articles {=nam} txt {=pri}, }", {"count": 2,  "articles": ({"nam": "Ur", "pri": 1}, {"nam": "Mo", "pri": 2})}),

        ("dear {=name}, {?market Please get the following groceries: \n \
            {#groceries Item: {=item}, {=count} pieces \n }} \
            {?deadline Be back before {=time}.}",
                 {"name": "Joe",
                "market": "True",
                "count": 5,
                "groceries": [dict(item="lemon", count=2), dict(item="cookies", count=4)],
                "deadline": True,
                "time": "17:30",
                 }
             ), # condition with repeat

        ("Contents: {#chapters Chapter {=name}. {#sections Section {=name}. }",
            {"chapters": [
                dict(name="Intro", sections=[dict(name="Foreword"), dict(name="Methodology")]),
                dict(name="Middle", sections=[dict(name="Measuring"), dict(name="Calculation"), dict(name="Results")]),
                dict(name="Epilogue", sections=[dict(name="Conclusion")])
                ]
             }), # Nested repeats.
        )

    for tems, temv in basictests+tests:
        print "Testcase: template = \"%s\", variables = %r" % (tems, temv)
        tem = Ovotemplate(tems)
        print
        tem.pprint()
        print "Expansion: \"%s\"" % tem.render(temv)
        print


    tp = u"""

    Beste {=naam},

    Bedankt voor je bestelling. De volgende artikelen
    zullen we zo snel mogelijk opsturen:

    {#levering
        {=artikel} €{=prijs} * {=aantal} stuks = €{=regtot}
    }

    {?backorder De volgende artikelen zijn nog in backorder:
        {#backartikels
            {=artikel} €{=prijs} * {=aantal} stuks
        }
    }


    {?buitenland Voor buitenlandse bestellingen wordt {=porto} euro in rekening gebracht.}

    """

    vars = {
        "naam": "Jan",
        "levering": (
            {"artikel": "Bestekset", "prijs": 35, "aantal": 1, "regtot": 35},
            {"artikel": "Schaal", "prijs": 10, "aantal": 2, "regtot": 20},
            {"artikel": "Theelepels", "prijs": 1.15, "aantal": 5, "regtot": 5},
            ),
        "backorder": True,
        "backartikels": (
                {"artikel": u"Théédoek", "prijs": 2.50, "aantal": 2},
                {"artikel": "Pannenset", "prijs": 79.95, "aantal": 1},
                ),
        "buitenland": False,
        "porto": "5 euro",
        }

    tem = Ovotemplate(tp)
    tem.pprint()
    content = tem.render(vars)
    print content

    """
    Voorbeeld nested reps:

    {#outer
        <h1>{=nr}. {=hoofdstuktitel}</h1>
        {#inner
            <h2>{=subnr}. {=subhoofdstuktitel}</h2>
        }
    }
    """