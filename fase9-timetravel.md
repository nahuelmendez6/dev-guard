### 🕰 Fase 9: Proyecto Final y "Viaje en el Tiempo" (Time    
  Travel: Replay & Forking)
  
  En esta fase convertiremos el motor de LangGraph en una      
  máquina del tiempo. Gracias al MemorySaver (Checkpointer)    
  configurado en fases anteriores, LangGraph guarda una        
  "instantánea" (snapshot) inmutable del estado después de cada
  paso.
  ──────
  ### 1. Conceptos Fundamentales: La Analogía con Git          
                                                               
   Concepto Git      │ Concepto LangGra… │ Función / Mecanismo
  ───────────────────┼───────────────────┼─────────────────────
   Commit SHA        │ checkpoint_id     │ Identificador único
                     │                   │ de cada estado en
                     │                   │ el tiempo
                     │                   │ (snapshot.config["c
                     │                   │ onfigurable"]["chec
                     │                   │ kpoint_id"]).
   git log           │ app.get_state_his │ Itera sobre todos
                     │ tory(config)      │ los checkpoints
                     │                   │ pasados de un
                     │                   │ thread_id (del más
                     │                   │ reciente al más
                     │                   │ antiguo).
   git checkout      │ Replay            │ Volver a ejecutar
   <commit>          │                   │ el grafo desde un
                     │                   │ checkpoint pasado
                     │                   │ pasando
                     │                   │ app.invoke(None,
                     │                   │ checkpoint_config).
   git commit --     │ Forking con       │ Modificar
   amend / rama      │ update_state()    │ manualmente
                     │                   │ variables del
                     │                   │ estado en un punto
                     │                   │ temporal y
                     │                   │ continuar la
                     │                   │ ejecución por una
                     │                   │ rama alternativa.
   HEAD              │ app.get_state(con │ El checkpoint más
                     │ fig)              │ reciente del hilo
                     │                   │ actual.
  ──────
  ### 2. Los Dos Superpoderes del Time Travel
  
  #### A. Replay (Repetición Exacta)
  
  Permite situarte en un punto del pasado y volver a ejecutarlo
  tal cual:
  
    # Tomamos la configuración de un checkpoint del pasado
    past_config = {
        "configurable": {
            "thread_id": "session-1",
            "checkpoint_id":
            "1f1ddd9b-xxxx-xxxx-xxxx-xxxxxxxxxxxx"             
        } 
    }
    # Al pasar None como input, LangGraph reanuda la acción  
    pendiente de ese checkpoint                                
    app.invoke(None, past_config)
  
  #### B. Forking & Modificación con update_state()            
  
  Permite alterar el estado en el pasado como si un nodo       
  hubiera devuelto otra cosa.
  
    # Modificamos el estado en ese checkpoint específico       
    new_config = app.update_state(
        past_config,
        values={"code": GeneratedCode(code="def suma(a, b):    
        return a + b", explanation="Fix manual")},             
        as_node="generate_code" # <-- CRUCIAL: le dice al grafo
        qué nodo "produjo" este cambio
    )
  
    # Reanudamos desde el nuevo estado modificado              
    app.invoke(None, new_config)                               
                                                               
  │ Important
  │ ¿Por qué es crucial as_node?
  │ Si indicas as_node="generate_code", el grafo sabrá que la  
  │ siguiente arista que debe consultar es la que sale de      
  │ generate_code (en nuestro caso, irá directo al nodo        
  │ validator), permitiéndonos saltarnos llamadas costosas a la
  │ API del LLM si decidimos corregir el código manualmente.   
  ──────
  ### 3. Plan de Implementación Paso a Paso
  
  Implementaremos la Fase 9 en 3 pasos estructurados:          
  
  │ Diagram exceeds terminal width (121 > 65 cols)             
  │ Displayed as code block. Widen terminal to view inline.    
  
    flowchart LR
        A["Paso 1: Módulo time_travel.py<br/>(Funciones Replay,
        Fork y Log)"] --> B["Paso 2:
        time_travel_demo.py<br/>(Demostración práctica         
        aislada)"]
        B --> C["Paso 3: Integración en main.py<br/>(Comandos  
        CLI: /historial, /fork, /replay)"]
  ──────
  #### 🛠 Paso 1: Crear src/agent/time_travel.py 
  
  Crearemos funciones utilitarias limpias y reutilizables para 
  inspeccionar el historial y manipular checkpoints:
  
  1. print_history(app, config, limit=10): Imprime una tabla
  tipo git log mostrando:
      • checkpoint_id (primeros 8 caracteres). 
      • step: paso del grafo.
      • next: qué nodo está a punto de ejecutarse (analizer,
      validator, user_approval o None si terminó).
      • Vista previa del estado actual (user_request, código 
      generado, errores).
  2. get_checkpoint_by_index(app, config, index): Permite     
  seleccionar un snapshot por su número de orden (0 = actual, 1
  = paso anterior, etc.).
  3. fork_state(app, target_config, updates, as_node=None):    
  Modifica el estado con update_state y devuelve la nueva      
  configuración lista para reanudar.                           
  4. replay_from(app, target_config): Reanuda la ejecución     
  desde el checkpoint seleccionado.
  ──────
  #### 🧪 Paso 2: Crear el script de demostración interactiva  
  time_travel_demo.py
  
  Un script guiado paso a paso para verificar el flujo:        
  
  1. Ejecuta una petición inicial: "Escribe una función de suma
  en Python con error de sintaxis".
  2. El grafo genera código con errores o pausa en
  user_approval.
  3. Navegamos al pasado: mostramos el historial de checkpoints.
  4. Seleccionamos el checkpoint justo antes de validar.       
  5. Inyectamos manualmente el código corregido con            
  update_state(..., as_node="generate_code").
  6. Reanudamos: el grafo pasa inmediatamente a validator y    
  luego a user_approval, ¡sin volver a gastar tokens en el LLM!
  ──────
  #### 💻 Paso 3: Integrar Time Travel en main.py (CLI         
  Interactivo)
  
  Añadiremos al bucle principal de la consola comandos directos
  para el usuario:
  
  • historial: Muestra los últimos checkpoints de la sesión    
  activa.
  • replay <id>: Vuelve a ejecutar desde un punto anterior.    
  • editar o fork: Permite al usuario editar el código generado
  en la memoria antes de aprobarlo o enviarlo al validador.
  ──────
  ### ¿Empezamos con el Paso 1 creando
  src/agent/time_travel.py?
  
  Confirmame si querés que procedamos a implementar los        
  archivos y probar el flujo en vivo.

───────────────────────────────────────────────