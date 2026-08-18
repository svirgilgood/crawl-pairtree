"""
This are post crawl clean up scripts to update some of the things that
need to be rearranged
"""

from pyoxigraph import Store


def clean_up(store: Store) -> Store:
    store.update("""    PREFIX    ark: <http://ark.lib.uchicago.edu/>
    PREFIX bf:        <http://id.loc.gov/ontologies/bibframe/>
    PREFIX continuum: <https://continuum.lib.uchicago.edu/ontology/>
    PREFIX contid:    <https://continuum.lib.uchicago.edu/item/>
    PREFIX premis:    <http://www.loc.gov/premis/rdf/v3/>
    PREFIX ebucore:   <http://www.ebu.ch/metadata/ontologies/ebucore/ebucore#>
    PREFIX dc:        <http://purl.org/dc/elements/1.1/>
    PREFIX dcterms:   <http://purl.org/dc/terms/>
    PREFIX xsd:       <http://www.w3.org/2001/XMLSchema#>
    PREFIX rdf:       <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs:      <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX edm:       <http://www.europeana.eu/schemas/edm/>
    PREFIX uchicago: <https://lib.uchicago.edu/>

    INSERT {
        ?fileNode
            premis:basis [
                premis:allows uchicago:DownloadAllowed ;
            ] ;
        .
    }
    WHERE {
        ?arkNode
            dc:rights ?rights ;
            ^dcterms:isPartOf ?fileNode ;
        .
        VALUES ?rights {
            <http://creativecommons.org/licenses/by-nc/4.0/>
            <https://rightsstatements.org/page/InC-NC/1.0/>
        }
        FILTER NOT EXISTS {
            ?fileNode premis:basis ?rule .
        }
    }
    """)
    store.update("""    PREFIX    ark: <http://ark.lib.uchicago.edu/>
       PREFIX bf:        <http://id.loc.gov/ontologies/bibframe/>
       PREFIX continuum: <https://continuum.lib.uchicago.edu/ontology/>
       PREFIX contid:    <https://continuum.lib.uchicago.edu/item/>
       PREFIX premis:    <http://www.loc.gov/premis/rdf/v3/>
       PREFIX ebucore:   <http://www.ebu.ch/metadata/ontologies/ebucore/ebucore#>
       PREFIX dc:        <http://purl.org/dc/elements/1.1/>
       PREFIX dcterms:   <http://purl.org/dc/terms/>
       PREFIX xsd:       <http://www.w3.org/2001/XMLSchema#>
       PREFIX rdf:       <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
       PREFIX rdfs:      <http://www.w3.org/2000/01/rdf-schema#>
       PREFIX edm:       <http://www.europeana.eu/schemas/edm/>
       PREFIX uchicago: <https://lib.uchicago.edu/>

       DELETE {
        ?arkNode
            premis:basis ?basisnode .
        ?basisnode
            ?premisCont ?ruleBN .
        ?ruleBN
            ?rulePred ?ruleObj .
        ?basisnode
            ?premisCont ?ruleNamedNode .
        ?arkNodeNamedRule
            premis:basis ?basisNamedRule .
        ?basisNamedRule
            ?premisNamedCont ?ruleNamedNode .
       }
       INSERT {
        ?fileNode premis:basis ?newbasisnode .
        ?newbasisnode ?premisCont ?rulenode .
        ?rulenode ?rulePred ?ruleObj .
        ?fileNamedRule premis:basis [
            ?premisNamedCont ?ruleNamedNode ;
        ] .
       }
        WHERE {
        {
            { SELECT ?arkNode ?fileNode ?basisnode ?newbasisnode ?rulenode
                WHERE {
                    ?arkNode
                        a edm:ProvidedCHO ;
                        premis:basis ?basisnode ;
                        ^dcterms:isPartOf ?fileNode ;
                    .
                    ?basisnode ?condition ?ruleBlank .
                    VALUES ?condition {
                        premis:allows
                        premis:disallows
                    }
                    BIND(BNODE() AS ?rulenode)
                    BIND(BNODE() AS ?newbasisnode)
                    FILTER(ISBLANK(?ruleBlank))
                }
            }
            ?arkNode
                premis:basis [
                ?premisCont  ?ruleBN ;
            ] .
            ?ruleBN
                ?rulePred ?ruleObj .
        } UNION {
            ?arkNodeNamedRule
                a edm:ProvidedCHO ;
                premis:basis ?basisNamedRule ;
                ^dcterms:isPartOf ?fileNamedRule ;
                .
            ?basisNamedRule ?premisNamedCont ?ruleNamedNode .
            FILTER(!ISBLANK(?ruleNamedNode))
            }
        }
            """)
    return store
