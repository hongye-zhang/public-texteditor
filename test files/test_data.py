"""Test data module to store document structures and other test data"""

# Test document content

SAMPLE_MARKDOWN = """
# Background

In 1809, Europe was embroiled in warfare, pitting revolutionary France against a series of coalitions in the Coalition Wars almost continuously since 1792. A brief period of peace followed the March 1802 Treaty of Amiens before British-French relations deteriorated, leading to the War of the Third Coalition in May 1803.

Britain was joined in their coalition by Sweden in 1804 and Russia and Austria in 1805. In August 1805, the 200,000-strong French Grande Armée invaded the German states, hoping to defeat Austria before Russian forces could intervene. The French emperor Napoleon successfully wheeled his army into the Austrian rear and defeated them at the Battle of Ulm, fought from 15 to 20 October. The Austrian capital, Vienna, was captured in November and a Russo-Austrian army was decisively defeated at the 2 December Battle of Austerlitz.

Austerlitz incited a major shift in the European balance of power. Prussia felt threatened in the region and, alongside Russia, declared war against France in the 1806 War of the Fourth Coalition. After French victories at the Battle of Jena-Auerstadt on 14 October, France occupied the Prussian capital, Berlin. France invaded Poland in November, where Russian forces were stationed, and occupied Warsaw. Russian and French armies fought in February 1807 at the violent, indecisive Battle of Eylau. The action in Poland culminated on 14 June 1807 when the French defeated Russia at the Battle of Friedland.

The resulting Treaty of Tilsit in July left France as the dominant power in Western Europe, with many client states including the Duchy of Warsaw. This weakened Prussia and allowed Russia to expand into Finland and South-Eastern Europe.

## Peninsular War

In 1807, France tried to force Portugal to join the Continental System, a commercial embargo against Britain. When the Portuguese prince regent, John, refused to join, Napoleon sent General Junot to invade Portugal in 1807, resulting in the six year Peninsular War. The war weakened the French empire's military, particularly after Spanish forces and civilians rebelled against France after Napoleon overthrew the Spanish king. After the French defeat at the Battle of Bailén, Napoleon took command of the French forces, defeating the Spanish armies before returning to France.

Jean-de-Dieu Soult drove the British out of Spain in the Battle of Corunna in January 1809.

In the beginning of 1809, the French client kingdom of Spain, ruled by Napoleon's brother Joseph Bonaparte, controlled much of Spain and northern Portugal. British and Portuguese forces under Arthur Wellesley launched new offensives from Spring 1809. Spanish regular armies including those led by General Joaquín Blake continued to fight and guerrilla activity in the countryside made French operations hazardous. A significant French presence, numbering 250,000 in June 1809, remained in the peninsula throughout the War of the Fifth Coalition.

The Napoleonic occupation of France's own ally Spain persuaded many in Austria that Napoleon could not be trusted and declaring war was the only way to prevent him from destroying the Habsburg monarchy. The Spanish guerrillas inspired popular resistance against Napoleon, and the Austrians hoped that French preoccupation in Spain would make it easier to defeat France.

## Austria plans for war

Austria hoped Prussia would assist them in a war with France but a letter from Prussian minister Baron von Stein discussing the negotiations was intercepted by French agents and published in the Le Moniteur Universel on 8 September. Napoleon confiscated Stein's holdings in Westphalia and pressured King Frederick William III into dismissing him, and Stein fled into exile in Austria.

On the same day that Stein was compromised the Convention of Paris agreed a timetable for the withdrawal of foreign troops from Prussia, where French garrisons had been in place since the end of the War of the Fourth Coalition. The withdrawal was contingent on the payment of heavy reparations, totalling 140 million francs, over 30 months. The Prussian Army was also limited in size to 42,000 men, one sixth of its pre-war total. The convention severely restricted the ability of the Prussian state to wage war.

France withdrew 108,000 troops from Germany, more than half their strength there, to reinforce the French armies in Spain in October 1808. This lent support to Stadion's pro-war faction at the Austrian court. Stadion recalled Klemens von Metternich, his ambassador to Paris, to convince others to support his plan and by December 1808 Emperor Francis I was persuaded to support the war.

Austria and Prussia requested that Britain fund their military campaigns and requested a British military expedition to Germany. In April 1809 the British treasury supplied £20,000 in credit to Prussia, with additional funds promised if Prussia opened hostilities with France. Austria received £250,000 in silver, with a further £1 million promised for future expenses. Britain refused to land troops in Germany but promised an expedition to the low countries and to renew their campaign in Spain.
"""
ANALYSIS_OUTPUT = """{
  "sections": [
    {
      "title": "Document Total",
      "type": "",
      "summary": "Coalition Wars Austerlitz aftermath Peninsular War, 1807-1814 Battle Corunna Austrian strategy Stein Compromised, Prussia Restrained, France Withdraws Military funding",
      "content_type": "",
      "start_line": 0,
      "end_line": 30,
      "children": [
        {
          "title": "Background",
          "type": "heading",
          "summary": "Coalition Wars Austerlitz aftermath Peninsular War, 1807-1814 Battle of Corunna Napoleonic threat Stein Compromised, Troop Withdrawal, Reparations, Prussian Army, French Troop Withdrawal, Pro-War Faction, Austrian Support. Military funding",
          "content_type": "technical",
          "start_line": 1,
          "end_line": 30,
          "children": [
            {
              "title": "Peninsular War",
              "type": "heading",
              "summary": "French invasion of Portugal, Peninsular War. French victory at Corunna. Napoleon's betrayal, Austria declares war.",      
              "content_type": "narrative",
              "start_line": 11,
              "end_line": 20
            },
            {
              "title": "Austria plans for war",
              "type": "heading",
              "summary": "Austria seeks Prussia's help, France intervenes. Stein exiled. France withdraws troops, Austria and Prussia request aid.",
              "content_type": "narrative",
              "start_line": 21,
              "end_line": 30
            }
          ]
        }
      ]
    }
  ],
  "total_lines": 31
}"""


def parse_document_analyzer_results(analyzer_output):
    """
    Parse the results from DocumentAnalyzer into a structured format
    
    Args:
        analyzer_output: Output from DocumentAnalyzer
        
    Returns:
        dict: Parsed results containing sections with their metadata
    """
    import json
    
    if isinstance(analyzer_output, str):
        try:
            analyzer_output = json.loads(analyzer_output)
        except json.JSONDecodeError:
            print("Error: Invalid JSON in analyzer_output")
            return {"sections": [], "total_lines": 0}
            
    def flatten_sections(section, sections_list):
        """Helper function to flatten nested sections into a list"""
        # Add current section
        if section.get("title"):  # Only add sections with titles
            sections_list.append({
                "title": section.get("title", ""),
                "type": section.get("type", "text"),
                "summary": section.get("summary", ""),  # Store summary separately
                "start_line": section.get("start_line", 0),
                "end_line": section.get("end_line", 0)
            })
        
        # Process children recursively
        for child in section.get("children", []):
            flatten_sections(child, sections_list)
    
    # Initialize results
    parsed_results = {
        "sections": [],
        "total_lines": analyzer_output.get("total_lines", 0)
    }
    
    # Process each top-level section
    sections = analyzer_output.get("sections", [])
    for section in sections:
        flatten_sections(section, parsed_results["sections"])
    
    return parsed_results

def test_section_finder(api_key: str = None):
    """Test the section finder with sample data."""
    from section_finder import SectionFinder
    import os
    import json
    
    
    
    # Initialize section finder with API key
    
        
    # Remove any whitespace or quotes
    api_key = api_key.strip().strip('"').strip("'")
    
    
    try:
        # Parse the pre-generated analysis output
        analyzer_output = json.loads(ANALYSIS_OUTPUT)
        parsed_results = parse_document_analyzer_results(analyzer_output)
        
        sections_output = {
            "status": "parsed",
            "sections": [
                {
                    "title": section["title"],
                    "type": section["type"],
                    "lines": f"{section['start_line']}-{section['end_line']}",
                    "content_preview": section.get("summary", "")[:100]  # Use summary instead of content
                }
                for section in parsed_results["sections"]
            ]
        }
       
        
        finder = SectionFinder(api_key)
        
        
        # Test query
        query = "What led to Austria's decision to go to war?"
        output = {"status": "query", "message": f"Analyzing query: {query}"}
        print(json.dumps(output, indent=2))
        
        # Run analysis using the parsed results
        try:
            
            result = finder.analyze_sections(query, parsed_results["sections"])
            if result:
                analysis_output = {
                    "status": "success",
                    "main_section": {
                        "title": result["main"]["title"],
                        "lines": result["main"]["lines"]
                    }
                }
                if result.get("supplement"):
                    analysis_output["supplementary_sections"] = [
                        {
                            "title": supp["title"],
                            "lines": supp["lines"],
                            "summary": supp["summary"]
                        }
                        for supp in result["supplement"]
                    ]
                print(json.dumps(analysis_output, indent=2))
            return result
        except Exception as e:
            output = {"status": "error", "message": f"Error running analysis: {str(e)}"}
            print(json.dumps(output, indent=2))
            return None
            
    except Exception as e:
        output = {"status": "error", "message": f"Error in test setup: {str(e)}"}
        print(json.dumps(output, indent=2))
        return None

if __name__ == "__main__":
    import os
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        exit(1)
    test_section_finder(api_key)
