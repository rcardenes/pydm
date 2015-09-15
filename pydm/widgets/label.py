from PyQt4.QtGui import QLabel, QApplication, QColor, QPalette
from PyQt4.QtCore import pyqtSignal, pyqtSlot, pyqtProperty, QState, QStateMachine, QPropertyAnimation, QString
from channel import PyDMChannel
class PyDMLabel(QLabel):
  #Tell Designer what signals are available.
  __pyqtSignals__ = ("send_value_signal(QString)",
                     "connected_signal()",
                     "disconnected_signal()", 
                     "no_alarm_signal()", 
                     "minor_alarm_signal()", 
                     "major_alarm_signal()", 
                     "invalid_alarm_signal()")
  
  #Internal signals, used by the state machine
  connected_signal = pyqtSignal()
  disconnected_signal = pyqtSignal()
  no_alarm_signal = pyqtSignal()
  minor_alarm_signal = pyqtSignal()
  major_alarm_signal = pyqtSignal()
  invalid_alarm_signal = pyqtSignal()
  
  #Usually, this widget will get this from its parent pydm application.  However, in Designer, the parent isnt a pydm application, and doesn't know what a color map is.  The following two color maps are provided for that scenario.
  local_alarm_severity_color_map = {
    0: QColor(0, 0, 0), #NO_ALARM
    1: QColor(200, 200, 20), #MINOR_ALARM
    2: QColor(240, 0, 0), #MAJOR_ALARM
    3: QColor(240, 0, 240) #INVALID_ALARM
  }
  local_connection_status_color_map = {
    False: QColor(0, 0, 0),
    True: QColor(0, 0, 0,)
  }
  
  def __init__(self, init_channel=None, parent=None):
    super(PyDMLabel, self).__init__(parent)
    self.setup_state_machine()
    self._channel = init_channel
    self.setText("PyDMLabel")
    
    
  # Can the state machine be implemented at a lower level, like a QWidget subclass? 
  def setup_state_machine(self):
    self.state_machine = QStateMachine(self)
    
    #We'll need to talk to the parent application to figure out what colors to use for a specific state.  If the parent application doesn't have a color map (this is true when we are in Designer) then use the local colors defined above.
    app = QApplication.instance()
    try:
      connection_status_color_map = app.connection_status_color_map
      alarm_severity_color_map = app.alarm_severity_color_map
    except AttributeError:
      connection_status_color_map = self.local_connection_status_color_map
      alarm_severity_color_map = self.local_alarm_severity_color_map
    
    #There are two connection states: Disconnected, and Connected.
    disconnected_state = QState(self.state_machine)
    disconnected_state.assignProperty(self, "color", connection_status_color_map[False])
    #connected_state is parallel because it will have sub-states for alarm severity.
    connected_state = QState(self.state_machine)
    #connected_state itself doesn't have any particular color, that is all defined by the alarm severity.
    
    self.state_machine.setInitialState(disconnected_state)
    
    disconnected_state.addTransition(self.connected_signal, connected_state)
    connected_state.addTransition(self.disconnected_signal, disconnected_state)
    
    #Now lets add the alarm severity states.
    no_alarm_state = QState(connected_state)
    no_alarm_state.assignProperty(self, "color", alarm_severity_color_map[0])
    minor_alarm_state = QState(connected_state)
    minor_alarm_state.assignProperty(self, "color", alarm_severity_color_map[1])
    major_alarm_state = QState(connected_state)
    major_alarm_state.assignProperty(self, "color", alarm_severity_color_map[2])
    invalid_alarm_state = QState(connected_state)
    invalid_alarm_state.assignProperty(self, "color", alarm_severity_color_map[3])
    connected_state.setInitialState(no_alarm_state)
    
    #Add the transitions between different severities.
    #This is a bunch, since any severity can transition to any other.
    no_alarm_state.addTransition(self.minor_alarm_signal, minor_alarm_state)
    no_alarm_state.addTransition(self.major_alarm_signal, major_alarm_state)
    no_alarm_state.addTransition(self.invalid_alarm_signal, invalid_alarm_state)
    minor_alarm_state.addTransition(self.no_alarm_signal, no_alarm_state)
    minor_alarm_state.addTransition(self.major_alarm_signal, major_alarm_state)
    minor_alarm_state.addTransition(self.invalid_alarm_signal, invalid_alarm_state)
    major_alarm_state.addTransition(self.no_alarm_signal, no_alarm_state)
    major_alarm_state.addTransition(self.minor_alarm_signal, minor_alarm_state)
    major_alarm_state.addTransition(self.invalid_alarm_signal, invalid_alarm_state)
    invalid_alarm_state.addTransition(self.no_alarm_signal, no_alarm_state)
    invalid_alarm_state.addTransition(self.minor_alarm_signal, minor_alarm_state)
    invalid_alarm_state.addTransition(self.major_alarm_signal, major_alarm_state)
    
    #Add a cool fade animation to a state transition.
    self.color_fade = QPropertyAnimation(self, "color", self)
    self.color_fade.setDuration(175)
    self.state_machine.addDefaultAnimation(self.color_fade)
    
    self.state_machine.start()
    
  @pyqtSlot(str)
  def recieveValue(self, new_value):
    self.setText(new_value)
    
  # -2 to +2, -2 is LOLO, -1 is LOW, 0 is OK, etc.  
  @pyqtSlot(int)
  def alarmStatusChanged(self, new_alarm_state):
    pass
  
  #0 = NO_ALARM, 1 = MINOR, 2 = MAJOR, 3 = INVALID  
  @pyqtSlot(int)
  def alarmSeverityChanged(self, new_alarm_severity):
    if new_alarm_severity == 0:
      self.no_alarm_signal.emit()
    elif new_alarm_severity == 1:
      self.minor_alarm_signal.emit()
    elif new_alarm_severity == 2:
      self.major_alarm_signal.emit()
    elif new_alarm_severity == 3:
      self.invalid_alarm_signal.emit()
    
  #false = disconnected, true = connected
  @pyqtSlot(bool)
  def connectionStateChanged(self, connected):
    if connected:
      self.connected_signal.emit()
    else:
      self.disconnected_signal.emit()
    
  #Define setter and getter for the "color" property, used by the state machine to change color based on alarm severity and connection.
  def getColor(self):
    return self.palette().windowText().color()

  def setColor(self, color):
    palette = self.palette()
    old_alpha = palette.windowText().color().alphaF()
    color.setAlphaF(old_alpha)
    palette.setColor(QPalette.WindowText, color)
    self.setPalette(palette)
    
  color = pyqtProperty(QColor, getColor, setColor)
  
  def getChannel(self):
    return QString.fromAscii(self._channel)
  
  def setChannel(self, value):
    if self._channel != value:
      self._channel = str(value)

  def resetChannel(self):
    if self._channel != None:
      self._channel = None
    
  channel = pyqtProperty("QString", getChannel, setChannel, resetChannel)

  def channels(self):
    return [PyDMChannel(address=self.channel, connection_slot=self.connectionStateChanged, value_slot=self.recieveValue, severity_slot=self.alarmSeverityChanged)]