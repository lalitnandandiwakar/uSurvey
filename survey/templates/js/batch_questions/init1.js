{% load template_tags %}
LAYOUT_OPTS = {
	    name: 'dagre',
	    padding: 5
	  };
cy = cytoscape({
  container: document.getElementById('batch_questions'),
  minZoom: 0.5,
  zoom: 0,
////  pan: { x: 0, y: 0 },
//  userPanningEnabled: true,
  boxSelectionEnabled: true,
  selectionType: 'single',
  maxZoom: 2,
  position: {x: 0, y: 0},
  style: [
    {
      selector: "node",
      css: {
        'shape': 'rectangle',
        'text-wrap': 'wrap',
        'text-valign': 'center',
        'text-halign': 'center',
        'height': '80px',
        'width' : '150px',
        'text-max-width': '150px',
        'font-size' : '10px',
        'padding-top': '10px',
        'padding-left': '10px',
        'padding-bottom': '10px',
        'padding-right': '10px',
        'background-color' : 'grey',

      }
    },
    {
        selector: '$node[^parent]',
        css: {
      	  'content': 'data(name)',
      	  'text-valign': 'top',     
        }
      },  
      {
          selector: '$node[parent]',
          css: {
        	 'content': 'data(text)',
          }
      },  
    {
      selector: 'edge',
      css: {
        'target-arrow-shape': 'triangle',
        'content' : 'data(condition)',
        'font-size': '8px',
      }
    },
    {
      selector: ':selected',
      css: {
        'background-color': 'tan',
        'line-color': 'black',
        'target-arrow-color': '#FFFFFF',
        'source-arrow-color': '#FFFFFF'
      }
    }
    
  ],
  
  elements: {
      nodes: [
          		{% for q_node in batch_question_tree %}
          		    { data: { id: 'c_{{q_node.identifier}}', name: '{{q_node.identifier}}'} },
               	    { data: {id: '{{q_node.identifier}}', identifier: '{{q_node.identifier}}', parent: '{{q_node.identifier}}', text: '{{ q_node.text }}',  key: '{{q_node.pk}}' , answer_type:'{{q_node.answer_type}}'},},
              {% endfor %}
	          
            ],
            edges: [
  	           {% if batch_question_tree %}              
	          		{% for q_node in batch_question_tree %}
	          			{% for flow in q_node.flows.all %}
	          	        	{ data: { id: "{{q_node.identifier}}_{{flow.next_question.identifier}}", source: "{{q_node.identifier}}", target: "{{flow.next_question.identifier}}", condition: "{{ flow | show_condition }}", }, },
	          	        {% endfor %}
	               	{% endfor %}
		      {% endif %}
            ]
  },
  
  layout: LAYOUT_OPTS,
});

QUES_VALIDATION_OPTS = {{ batch | quest_validation_opts }} //QUES_VALIDATION_OPTS['answer_type'] = [validation_opts, val_opt2, ...]
ARGS_COUNT_MAP = {{ batch | validation_args }} //number of arguments for each arg count eg.  ARGS_COUNT_MAP['contains'] = 2, ARGS_COUNT_MAP['greater_than'] = 1 
