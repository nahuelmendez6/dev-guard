 ### 1. Fundamentos: ¿Cómo funciona Human-in-the-Loop en LangGraph moderno?         
                                                                                     
  En versiones modernas de LangGraph (a partir de v0.2/v1.x), la intervención humana 
  se basa en dos piezas clave de langgraph.types:                                    
                                                                                     
  1. interrupt(valor_para_el_humano):                                                
      • Se invoca dentro de cualquier nodo.                                          
      • Congela inmediatamente la ejecución del grafo en ese punto exacto.           
      • El argumento que le pasas (por ejemplo: { "accion": "escribir_disco",        
      "codigo": "..." }) es devuelto al llamador del grafo en el diccionario de      
      respuesta (bajo la clave __interrupt__).                                       
      • Guarda el estado en el checkpointer (el MemorySaver que ya configuraste en la
      Fase 6) asociado a tu thread_id.                                               
  2. Command(resume=valor_del_humano):                                               
      • Cuando el usuario humano decide (aprueba, rechaza o da feedback), vuelves a  
      llamar a:                                                                      
        app.invoke(Command(resume=tu_decision), config=config)                       
                                                                                     
      • Al usar el mismo thread_id, LangGraph despierta el grafo en el nodo congelado
      y hace algo mágico: la función interrupt() retorna el valor que enviaste en    
      resume.                                                                        
      • El nodo continúa ejecutando las líneas siguientes al interrupt() como si     
      fuera una función normal.                                                      
                                                                                     
                                                                                     
           [Generar Código]                                                          
                  │                                                                  
          [Validar Sintaxis]                                                         
                  │ (si es válido)                                                   
          ┌───────▼──────────────────────────┐                                       
          │ Nodo Sensible (ej. Guardar)      │                                       
          │   1. interrupt(info_al_humano) ──┼──► ⏸ Pausa y sale al usuario          
          │   2. Espera Command(resume=...) ◄┼──► ▶ Reanuda con la decisión          
          │   3. Si aprobado -> Escribe      │                                       
          │   4. Si rechazado -> Cancela     │                                       
          └───────┬──────────────────────────┘                                       
                  ▼                                                                  
                [END]                                                                
  ──────                                                                             
  ### 2. El Plan de Implementación para tu proyecto dev-guard                        
                                                                                     
  Actualmente tu flujo en graph.py es:                                               
                                                                                     
  1. analizer -> route_after_analysis -> generate_code                               
  2. generate_code -> validator                                                      
  3. validator -> route_after_validation -> si es correcto -> END.                   
                                                                                     
  Para la Fase 7, vamos a intercalar un nodo de operación sensible antes de END:     
                                                                                     
  1. Definir la operación sensible:                                                  
  Crear un nodo (por ejemplo save_code_node o apply_changes_node) que reciba el      
  código generado y pregunte al usuario si desea guardarlo en el disco (o en un      
  archivo concreto como output.py).                                                  
  2. Actualizar el Estado (state.py):                                                
  Agregar un campo opcional para reflejar el resultado de la acción humana (por      
  ejemplo saved_to_disk: bool).                                                      
  3. Crear el Nodo Sensible (nodes.py):                                              
  Implementar la función del nodo usando from langgraph.types import interrupt.      
  4. Actualizar el Grafo (graph.py):                                                 
      • Registrar el nuevo nodo.                                                     
      • Redirigir el caso de éxito en route_after_validation hacia este nuevo nodo en
      vez de END.                                                                    
      • Conectar este nodo con END.                                                  
  5. Simular la Interacción Humana:                                                  
  En el bloque if __name__ == "__main__":, ejecutar la primera llamada, comprobar que
  el grafo se detiene con __interrupt__, y luego enviar la respuesta con             
  Command(resume=...).                                                               
  ──────                                                                             
  ### 3. Guía Paso a Paso detallada                                                  
                                                                                     
  #### Paso 1: Actualizar state.py                                                   
                                                                                     
  Añade a tu AgentState un atributo para saber si la operación sensible fue          
  completada o rechazada:                                                            
                                                                                     
  • Por ejemplo: saved_to_disk: bool | None (o approved_by_user: bool).              
                                                                                     
  #### Paso 2: Crear el nodo sensible en nodes.py                                    
                                                                                     
  Importa interrupt:                                                                 
                                                                                     
    from langgraph.types import interrupt                                            
                                                                                     
  Crea una nueva función, por ejemplo save_code_to_disk_node(state: AgentState) ->   
  dict:                                                                              
                                                                                     
  • Obtén el código de state["code"].code.                                           
  • Llama a interrupt(...) pasándole los datos necesarios para que el humano juzgue  
  la acción:                                                                         
    decision = interrupt({                                                           
        "action": "write_file",                                                      
        "target_file": "generated_code.py",                                          
        "code_preview": code                                                         
    })                                                                               
  (Nota: en este punto la ejecución se pausará hasta que se reanude con              
  Command(resume=...)).                                                              
  • Procesa decision:                                                                
      • Si el humano aprobó (por ejemplo decision == "yes" o decision.get("approved")
      is True):                                                                      
          • Escribes el archivo en disco (o simulas la escritura imprimiendo         
          [Guardado exitoso]).                                                       
          • Retornas {"saved_to_disk": True}.                                        
      • Si el humano rechazó:                                                        
          • Imprimes [Operación cancelada por el usuario].                           
          • Retornas {"saved_to_disk": False}.                                       
                                                                                     
                                                                                     
                                                                                     
  #### Paso 3: Conectar el nuevo nodo en graph.py                                    
                                                                                     
  1. Importa tu nuevo nodo desde nodes.py.                                           
  2. En route_after_validation:                                                      
      • Cuando no haya errores sintácticos (len(errors) == 0), en lugar de retornar  
      "end", haz que retorne "save_code" (el nombre que le des al nuevo nodo).       
  3. En build_graph():                                                               
      • Añade el nodo: builder.add_node("save_code", save_code_to_disk_node).        
      • En el mapeo condicional de route_after_validation, actualiza el destino de   
      éxito para apuntar a "save_code".                                              
      • Añade la arista final: builder.add_edge("save_code", END).                   
                                                                                     
  
  #### Paso 4: Probar la interrupción y la reanudación interactiva
  
  Para probarlo en tu if __name__ == "__main__": en graph.py:
  
  1. Importa Command:
    from langgraph.types import Command
  
  2. Ejecutas el grafo normalmente con tu petición de código inicial:
    state_salida = app.invoke(initial_state, config=config)
  
  3. Si el código pasa las validaciones, la ejecución se pausará y state_salida      
  contendrá __interrupt__.
  Puedes verificar el estado de pausa con:
    snapshot = app.get_state(config)
    print("¿Está pausado en algún nodo?:", snapshot.next)
  
  4. Pides aprobación por consola o defines la decisión (por ejemplo decision =      
  {"approved": True} o {"approved": False}).
  5. Reanudas la ejecución inyectando la respuesta:
    resultado_final = app.invoke(Command(resume=decision), config=config)            
    print("Resultado final:", resultado_final)
  
  ──────
  ¿Tiene sentido la estructura del flujo? Dime si quieres empezar por el Paso 1      
  (actualizar el AgentState) y lo vamos revisando juntos conforme lo escribes.       

──────────────────────────────────────────────────────────────────