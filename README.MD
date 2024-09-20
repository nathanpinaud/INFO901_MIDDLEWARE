PINAUD Nathan

# Intergiciel (Middleware) avec Horloge de Lamport et Gestion de Section Critique Distribuée

## HOW TO

Ouvrir le fichier Com.html

## Introduction

Ce projet consiste en la réalisation d'un intergiciel (middleware) qui implémente un système de communication entre des processus utilisant l'horloge de Lamport pour la synchronisation des messages. Le middleware gère également la section critique distribuée avec un système de jeton en anneau, ainsi que la communication asynchrone et synchrone entre les processus.

## Architecture

Le middleware est composé de deux composants principaux :

1. **Processus** : Chaque processus instancie un communicateur et interagit avec les autres processus via ce communicateur.
2. **Communicateur (Com)** : Le communicateur est responsable de la gestion de la communication entre les processus, de la gestion de l'horloge de Lamport et de la section critique distribuée.

### Responsabilités du Communicateur :

- **Communication asynchrone** :

  - `broadcast(Object o)` : Envoie l'objet `o` à tous les processus dans leur boîte aux lettres (B.a.L.).
  - `sendTo(Object o, int dest)` : Envoie l'objet `o` au processus identifié par `dest`.

- **Section critique distribuée** :

  - `requestSC()` : Bloque le processus jusqu'à obtention de la section critique.
  - `releaseSC()` : Libère la section critique.

- **Communication synchrone** :

  - `broadcastSync(Object o, int from)` : Si le processus a l'identifiant `from`, il envoie l'objet `o` à tous les autres processus et attend que tous aient reçu le message.
  - `sendToSync(Object o, int dest)` et `receiveFromSync(Object o, int from)` : Envoie ou reçoit un message de manière synchrone et bloquante.

- **Synchronisation** :

  - `synchronize()` : Attend que tous les processus aient invoqué cette méthode avant de continuer.

- **Numérotation automatique** :
  - Chaque processus connecté reçoit un numéro unique à son lancement.
- **Heartbeat** :
  - Un système de "heartbeat" envoie périodiquement des messages de vie aux autres processus. Si un processus ne répond plus, la numérotation est corrigée.

## Détails techniques

### Gestion de l'horloge de Lamport

Le communicateur implémente une horloge de Lamport protégée par un sémaphore. Cela garantit qu'aucun conflit ne survient si plusieurs processus tentent de modifier l'horloge simultanément. La méthode `inc_clock()` permet à un processus d'incrémenter manuellement l'horloge s'il le souhaite.

Les messages système, tels que le passage de jeton pour la gestion de la section critique, n'affectent pas l'horloge de Lamport. Seuls les messages utilisateur influencent l'horloge.

### Boîte aux lettres (B.a.L.)

Chaque processus dispose d'une boîte aux lettres où sont stockés les messages reçus de manière asynchrone. Les processus peuvent piocher dans cette boîte aux lettres à tout moment pour traiter les messages à leur propre rythme.

### Section critique avec jeton en anneau

La gestion de la section critique se fait à l'aide d'un jeton qui circule entre les processus dans un anneau. Un thread dédié dans le communicateur gère la circulation du jeton. La réception d'un message contenant le jeton ne modifie pas l'horloge de Lamport, car il s'agit d'un message système.

### Numérotation des processus

Les processus sont numérotés automatiquement et consécutivement dès leur connexion. En cas de défaillance d'un processus, les autres processus renumérotent automatiquement ceux encore en vie.

### heartbeat

Chaque processus envoie périodiquement un "heartbit" à tous les autres processus pour signaler qu'il est toujours actif. Si un processus ne reçoit pas de heartbeat d'un autre processus pendant une certaine période, il le considère comme déconnecté.
