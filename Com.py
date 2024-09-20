import random
from time import sleep
from typing import Callable, List

from Mailbox import Mailbox

from pyeventbus3.pyeventbus3 import PyBus, subscribe, Mode

from Message import *

class Com:
    """
    Classe communication
    Permet de gérer la communication entre les processus
    """

    def __init__(self, nbProcess):
        self.nbProcess = nbProcess
        self.myId = None
        self.listInitId = []

        self.aliveProcesses = []
        self.maybeAliveProcesses = []

        PyBus.Instance().register(self, self)
        sleep(1)

        self.mailbox = Mailbox()
        self.beatCheck = None
        self.clock = 0

        self.nbSync = 0
        self.isSyncing = False

        self.tokenState = TokenState.Null
        self.currentTokenId = None

        self.isBlocked = False
        self.awaitingFrom = []
        self.recvObj = None

        self.alive = True
        if self.getMyId() == self.nbProcess - 1:
            self.currentTokenId = random.randint(0, 10000 * (self.nbProcess - 1))
            self.sendToken()
        self.startHeartbeat()

    def getNbProcess(self) -> int:
        """
        :return: le nombre de processus
        """

        return self.nbProcess

    def getMyId(self) -> int:
        """
        :return: l'id du processus
        """
 
        if self.myId is None:
            self.initMyId()
        return self.myId

    def initMyId(self):
        """
        Initialise l'id du processus
        :return: None
        """
        randomNb = random.randint(0, 10000 * (self.nbProcess - 1))
        print(self, ["My random id is:", randomNb])
        self.sendMessage(InitIdMessage(randomNb))
        sleep(2)
        if len(set(self.listInitId)) != self.nbProcess:
            print("Conflict, retrying")
            self.listInitId = []
            return self.initMyId()
        self.listInitId.sort()
        self.myId = self.listInitId.index(randomNb)
        print("My id is :", self.myId, "and my list is :", self.listInitId, "and my random is :", randomNb,)

    @subscribe(threadMode=Mode.PARALLEL, onEvent=InitIdMessage)
    def onReceiveInitIdMessage(self, message: InitIdMessage):
        """
        Listener pour les messages d'initialisation d'id
        :param message: le message reçu
        :return: None
        """

        print("Received init id message with random equal to", message.getObject())
        self.listInitId.append(message.getObject())

    def sendMessage(self, message: Message):
        """
        Envoie un message
        :param message: le message à envoyer
        :return: None
        """

        if not message.is_system:
            self.incClock()
            message.horloge = self.clock
        print(message)
        PyBus.Instance().post(message)

    def sendTo(self, obj: any, com_to: int):
        """
        Envoie un message à un processus spécifique
        :param obj: le message à envoyer
        :param com_to: le processus destinataire
        :return: None
        """

        self.sendMessage(MessageTo(obj, self.getMyId(), com_to))

    @subscribe(threadMode=Mode.PARALLEL, onEvent=MessageTo)
    def onReceive(self, message: MessageTo):
        """
        Listener pour les messages
        :param message: le message reçu
        :return: None
        """

        if message.to_id != self.getMyId() or type(message) in [MessageToSync, Token, AcknowledgementMessage]:
            return
        if not message.is_system:
            self.clock = max(self.clock, message.horloge) + 1
        print("Received MessageTo from", message.from_id, ":", message.getObject())
        self.mailbox.addMessage(message)

    def sendToSync(self, obj: any, com_to: int):
        """
        Envoie un message synchrone
        :param obj: le message à envoyer
        :param com_to: le processus destinataire
        :return: None
        """

        self.awaitingFrom = com_to
        self.sendMessage(MessageToSync(obj, self.getMyId(), com_to))
        while com_to == self.awaitingFrom:
            if not self.alive:
                return

    def recevFromSync(self, com_from: int) -> any:
        """
        Recoit un message synchrone
        :param com_from: le processus expéditeur
        :return: le message reçu
        """

        self.awaitingFrom = com_from
        while com_from == self.awaitingFrom:
            if not self.alive:
                return
        ret = self.recvObj
        self.recvObj = None
        return ret

    @subscribe(threadMode=Mode.PARALLEL, onEvent=MessageToSync)
    def onReceiveSync(self, message: MessageToSync):
        """
        Listener pour les messages synchrone
        :param message: le message reçu
        :return: None
        """

        if message.to_id != self.getMyId():
            return
        if not message.is_system:
            self.clock = max(self.clock, message.horloge) + 1
        while message.from_id != self.awaitingFrom:
            if not self.alive:
                return
        self.awaitingFrom = -1
        self.recvObj = message.getObject()
        self.sendMessage(AcknowledgementMessage(self.getMyId(), message.from_id))

    def broadcastSync(self, com_from: int, obj: any = None) -> any:
        """
        Broadcast synchrone
        :param com_from: le processus expéditeur
        :param obj: le message à envoyer
        :return: le message reçu
        """

        if self.getMyId() == com_from:
            print("Broadcasting synchroneously", obj)
            for i in range(self.nbProcess):
                if i != self.getMyId():
                    self.sendToSync(obj, i, 99)
        else:
            return self.recevFromSync(com_from)

    @subscribe(threadMode=Mode.PARALLEL, onEvent=AcknowledgementMessage)
    def onAckSync(self, event: AcknowledgementMessage):
        """
        Listener pour les messages d'acquittement synchrone
        :param event: le message reçu
        :return: None
        """

        if self.getMyId() == event.to_id:
            print("Received AcknowledgementMessage from", event.from_id)
            self.awaitingFrom = -1

    def synchronize(self):
        """
        Synchronise les processus
        :return: None
        """

        self.isSyncing = True
        print("Synchronizing")
        while self.isSyncing:
            sleep(0.1)
            print("Synchronizing in")
            if not self.alive:
                return
        while self.nbSync != 0:
            sleep(0.1)
            print("Synchronizing out")
            if not self.alive:
                return
        print("Synchronized")

    def requestSC(self):
        """
        Demande la section critique
        :return: None
        """

        print("Requesting SC")
        self.tokenState = TokenState.Requested
        while self.tokenState == TokenState.Requested:
            if not self.alive:
                return
        print("Received SC")

    def releaseSC(self):
        """
        Relache la section critique
        :return: None
        """

        print("Releasing SC")
        if self.tokenState == TokenState.SC:
            self.tokenState = TokenState.Release
        self.sendToken()
        self.tokenState = TokenState.Null
        print("Released SC")

    def broadcast(self, obj: any):
        """
        Broadcast
        :param obj: le message à envoyer
        :return: None
        """

        self.sendMessage(BroadcastMessage(obj, self.getMyId()))

    @subscribe(threadMode=Mode.PARALLEL, onEvent=BroadcastMessage)
    def onBroadcast(self, message: BroadcastMessage):
        """
        Listener pour les messages broadcast
        :param message: le message reçu
        :return: None
        """

        if message.from_id == self.getMyId() or type(message) in [HeartbeatMessage]:
            return
        print("Received broadcasted message from", message.from_id, ":", message.getObject())
        if not message.is_system:
            self.clock = max(self.clock, message.horloge) + 1
        self.mailbox.addMessage(message)

    def sendToken(self):
        """
        Envoie le jeton
        :return: None
        """

        if self.currentTokenId is None:
            return
        sleep(0.1)
        self.sendMessage(Token(self.getMyId(), (self.getMyId() + 1) % self.nbProcess, self.nbSync, self.currentTokenId))
        self.currentTokenId = None


    def incClock(self):
        """
        Incrémente l'horloge
        :return: None
        """

        self.clock += 1

    def getClock(self) -> int:
        """
        :return: l'horloge
        """

        return self.clock

    def stop(self):
        """
        Arrête la communication
        :return: None
        """
        self.alive = False

    @subscribe(threadMode=Mode.PARALLEL, onEvent=Token)
    def onToken(self, event: Token):
        """
        Listener pour les messages de jeton
        :param event: le message reçu
        :return: None
        """

        if event.to_id != self.getMyId() or not self.alive:
            return
        print("Received token from", event.from_id)
        self.currentTokenId = event.currentTokenId
        self.nbSync = event.nbSync + int(self.isSyncing)% self.nbProcess
        self.isSyncing = False
        if self.tokenState == TokenState.Requested:
            self.tokenState = TokenState.SC
        else:
            self.sendToken()

    def doCriticalAction(self, funcToCall: Callable, *args: List[any]) -> any:
        """
        Fait une action critique
        :param funcToCall: la fonction à appeler
        :param args: les arguments de la fonction
        :return: le retour de la fonction
        """

        self.requestSC()
        ret = None
        if self.alive:
            if args is None:
                ret = funcToCall()
            else:
                ret = funcToCall(*args)
            self.releaseSC()
        return ret

    def startHeartbeat(self):
        """
        Démarre le heartbeat
        :return: None
        """

        self.sendMessage(StartHeartbeatMessage(self.getMyId()))

    @subscribe(threadMode=Mode.PARALLEL, onEvent=StartHeartbeatMessage)
    def onStartHeartbeat(self, event: StartHeartbeatMessage):
        """
        Listener pour les messages de démarrage de heartbeat
        :param event: le message reçu
        :return: None
        """
        if event.from_id != self.getMyId():
            return
        self.heartbeat()

    def heartbeat(self):
        """
        Heartbeat
        :return: None
        """
        print(self, "Starting heartbeat")
        while self.alive:
            self.sendMessage(HeartbeatMessage(self.getMyId()))
            sleep(0.1)

            self.beatCheck = True
            print("Checking heartbeat")
            print(["Alive processes", self.aliveProcesses])
            print(["Dead processes", self.maybeAliveProcesses])
            tmpMaybeAliveProcesses = [idMaybeDead for idMaybeDead in range(self.nbProcess) if idMaybeDead != self.getMyId() and idMaybeDead not in self.aliveProcesses]
            print(["Maybe alive processes", tmpMaybeAliveProcesses])
            self.aliveProcesses = []
            for idDeadProcess in self.maybeAliveProcesses:
                if idDeadProcess < self.getMyId():
                    self.myId -= 1
                    print("My id changed from ", self.getMyId()+1, "to", self.getMyId())
                tmpMaybeAliveProcesses = [(idMaybeDead - 1 if idMaybeDead > idDeadProcess else idMaybeDead) for idMaybeDead in tmpMaybeAliveProcesses]
                self.nbProcess -= 1
            self.maybeAliveProcesses = tmpMaybeAliveProcesses
            print("Heartbeat Checked")
            self.beatCheck = False

    @subscribe(threadMode=Mode.PARALLEL, onEvent=HeartbeatMessage)
    def onHeartbeat(self, event: HeartbeatMessage):
        """
        Listener pour les messages de heartbeat
        :param event: le message reçu
        :return: None
        """
        
        while self.beatCheck:
            pass
        if event.from_id == self.getMyId():
            return
        print("Received heartbeat from", event.from_id)
        if event.from_id in self.maybeAliveProcesses:
            self.maybeAliveProcesses.remove(event.from_id)
        if event.from_id not in self.aliveProcesses:
            self.aliveProcesses.append(event.from_id)
