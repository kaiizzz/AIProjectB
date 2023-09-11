# COMP30024 Artificial Intelligence, Semester 1 2023
# Project Part B: Game Playing Agent

import copy
from dataclasses import dataclass
from referee.game import \
    PlayerColor, Action, SpawnAction, SpreadAction, HexPos, HexDir
from .utils import render_board
from .coverage import getCoverages, peaceful, evaluateAtkDef
#import random
import math

# This is the entry point for your game playing agent. Currently the agent
# simply spawns a token at the centre of the board if playing as RED, and
# spreads a token at the centre of the board if playing as BLUE. This is
# intended to serve as an example of how to use the referee API -- obviously
# this is not a valid strategy for actually playing the game!

BREADTH = 5
DEPTH = 5

DIM = 7
MAX_POWER = DIM - 1
MAX_BOARD_POW = 49
MAX_TURNS = 343

DIRECTIONS = ((1,-1), (1,0), (0,1), (-1,1), (-1,0), (0,-1))
ENEMY = {'r': 'b', 'b': 'r'}

################################################################################
############################## Agent Class #####################################
################################################################################

class Agent:
    def __init__(self, color: PlayerColor, **referee: dict):
        """
        Initialise the agent.
        """
          
        self.colour = None
        self.board = Board()
        #self.Minimax = minimax(self.board)
        self.Minimax = minimax()
        match color:
            case PlayerColor.RED:
                print("Testing: I am playing as red")
                self.colour = 'r'
            case PlayerColor.BLUE:
                print("Testing: I am playing as blue")
                self.colour = 'b'

    def action(self, **referee: dict) -> Action:
        """
        Return the next action to take.
        """
        ######## calling minimax algorithm for next move ########
        next_move = self.Minimax.next_move(self.board, self.colour)
            
        if (next_move[0] == 'spread'):
                return SpreadAction(HexPos(next_move[1][0], next_move[1][1]), HexDir(next_move[2]))
        else:
                return SpawnAction(HexPos(next_move[1][0], next_move[1][1]))
       
                    
                   
    ### DOES IT ACCOUNT FOR OPPONENT"S SPAWNS AND SPREADS? AND PLAYER SPREADS THAT GOES OVER MAX POWER?
    def turn(self, color: PlayerColor, action: Action, **referee: dict):
        """
        Update the agent with the last player's action.
        Note: this updates your agent as well.
        """

        match action:
            case SpawnAction(cell):
                #print(f"Testing: {color} SPAWN at {cell}")
                c = 'r'
                if (color == PlayerColor.BLUE):
                    c = 'b'
                #self.board.totalPower += 1
                self.board.spawn((cell.r, cell.q), c)
                return
            
            ### NEED TO RE-CALCULATE POWER for any SPREADS?
            case SpreadAction(cell, direction):
                #print(f"Testing: {color} SPREAD from {cell}, {direction}")
                self.board.spread((cell.r, cell.q), (direction.value.r, direction.value.q))
                #self.board.totalPower = getTotalPower(self.board.board)
                return

################################################################################
########################### Ineternal Board Class ##############################
################################################################################

@dataclass
class Board:
    """
    A data structure to represent the internal state of the board.
    """
    
    def __init__(self):
        # Initialise the internal board.
        self.board: dict[tuple, tuple] = {}

    def spawn(self, position: tuple, color):
        """ Spawns a piece (its position) on the board """
        self.board[position] = (color, 1)
    

    def countPieces(self, color: str):
        """ Counts the number of pieces on the board for a given color """
        count = 0
        for piece in self.board.keys():
            if self.board.get(piece)[0] == color:
                count += 1
        return count

    def spread(self, piece: tuple, direction: tuple):
        """ Spreads a piece (its position) in a direction on the board """
        colour = self.board.get(piece)[0]
        spreadDistance = self.board.get(piece)[1]

        temp = piece 

        # go through all the spread distance
        while spreadDistance:
            newPosition = self.findNewPosition(temp, direction)
            self.spreadToNode(newPosition, colour)

            # set temp to new position to use again next iteration
            temp = newPosition

            spreadDistance -= 1

        # delete original piece from board
        del self.board[piece]
            

    def findNewPosition(self, position, direction):
        """ Finds the destination of a node after a move in a direction """

        newR = position[0] + direction[0]
        newQ = position[1] + direction[1]

        # require both r and q to be positive, and also less than the dimension
        if newR < 0:
            newR = DIM - 1
        elif newR >= DIM:
            newR = 0

        if newQ < 0:
            newQ = DIM - 1
        elif newQ >= DIM:
            newQ = 0

        return (newR, newQ)

    def spreadToNode(self, newPosition, colour):
            """ 
            Increments power of a node and changes its colour if it is an enemy node, 
            or removing the node if the max power is reached 
            """
            if newPosition not in self.board.keys():
                self.board[newPosition] = (colour, 1)    
            else:
                power = self.board.get(newPosition)[1]
                if power == MAX_POWER:
                    self.board.pop(newPosition)
                else:
                    self.board[newPosition] = (colour, 1 + power)
            return
    
    def getValues(self):
        return self.board.values()
    
    def getKeys(self):
        return self.board.keys()
    
    def checkEndGame(self, colour):
        """ Checks if the game is about to end for the other player """
        c = 'r'
        if colour == 'r':
            c = 'b'
        
        if  countColour(self.board, c) == 1:
            return True
        else:
            return False
    
    def endgameAction(self, colour):
        """ Performs the action for the endgame """
        # find the last piece on the board
        c = 'r'
        if colour == 'r':
            c = 'b'
        temp = copy.deepcopy(self)
        for piece in self.board.keys():
            if self.board.get(piece)[0] == colour:
                # spread the piece in all directions
                for direction in DIRECTIONS:
                    temp.spread(piece, direction)
                    if countColour(temp.board, c) == 0:
                        return ('spread', piece, direction)
                    temp = copy.deepcopy(self) # reset temp to original state
        return None


################################################################################
######################## Minimax helper functions ##############################
################################################################################   
    
def get_successors(state: Board, colourToMove):
    """ gets the successors, possible states we need to explore """
    successors = []

    # do we need to copy board into state? just use the board argument
    temp = copy.deepcopy(state)
    
    # loop through the board and find all player's piece
    # when you land on a piece perform a spread in 6 directions
    # if it is empty spawn a piece
    # add to the successors list
    
    coverages = getCoverages(state.board)
    colourToMoveCoverage = None
    colourJustPlayedCoverage = None

    if colourToMove == 'r':
        colourToMoveCoverage = coverages[0]
        colourJustPlayedCoverage = coverages[1]
    else:
        colourToMoveCoverage = coverages[1]
        colourJustPlayedCoverage = coverages[0]
    
    #spreads = []
    for position in state.board.keys():
        if(state.board.get(position)[0] == colourToMove):
            # spread in all directions
            for direction in DIRECTIONS:
                temp.spread(position, direction)
                #temp.turn += 1
                successors.append((temp, ('spread', position, direction)))
                #spreads.append((temp, ('spread', position, direction)))
                temp = copy.deepcopy(state) # reset temp to original state
    
    #spawns = []
    if getTotalPower(state.board) < MAX_BOARD_POW:
        #temp = copy.deepcopy(state)
        for r in range(DIM):
            for q in range(DIM):
                if (r,q) not in state.board.keys():
                    playerCoverage = colourToMoveCoverage[r,q]
                    if playerCoverage >= colourJustPlayedCoverage[(r,q)]:
                        temp.spawn((r, q), colourToMove)
                        #temp.turn += 1
                        successors.append((temp, ('spawn', (r, q), colourToMove)))
                        #spawns.append((temp, ('spawn', (r, q), colourToMove)))
                        temp = copy.deepcopy(state)
    

    bestForPower = None
    # person just moved is r --> next to move is b, vice versa
    if colourToMove == 'r':
        successors = sorted(successors, key = lambda x: evaluateAtkDef(x[0].board, 'b'), reverse=True)
        bestForPower = max(successors, key = lambda x: evaluatePower(x[0].board))
    else:
        successors = sorted(successors, key = lambda x: evaluateAtkDef(x[0].board, 'r'))
        bestForPower = min(successors, key = lambda x: evaluatePower(x[0].board))
    
    b = min(len(successors), BREADTH)

    chosenSuccessors = successors[0:(b-1)]

    if bestForPower in chosenSuccessors:
        chosenSuccessors.remove(bestForPower)
    else:
        chosenSuccessors.pop()

    chosenSuccessors.insert(0, bestForPower)

    return chosenSuccessors


    #if colourToMove == 'r':
    #    spawns = sorted(spawns, key = lambda x: evaluateAtkDef(x[0].board, 'b'), reverse=True)
    #    spreads = sorted(spreads, key = lambda x: evaluateAtkDef(x[0].board, 'b'), reverse=True)
    #else:
    #    spawns = sorted(spawns, key = lambda x: evaluateAtkDef(x[0].board, 'r'))
    #    spreads = sorted(spreads, key = lambda x: evaluateAtkDef(x[0].board, 'r'))

    #b = min(len(spreads), BREADTH - 1)

    #successors = spreads[0:(b-1)]

    #if spawns:
    #    successors.append(spawns[0])
    #elif len(spreads) > b:
    #    successors.append(spreads[b])

    #return successors



# higher power favours red, lower power favours blue
def evaluatePower(board: dict[tuple, tuple]):
    """"""
    totalPower = 0
    for v in board.values():
        if v[0] == 'r':
            totalPower += v[1]
        else:
            totalPower -= v[1]
    return totalPower

def getTotalPower(board):
    power = 0
    for (_, k) in board.values():
        power += k
    return power

def countColour(board, colour):
    total = 0
    for (_, (c, _)) in board.items():
        if c == colour:
            total += 1

    return total


################################################################################
############################# Minimax Class ####################################
################################################################################

class minimax:
    
    def __init__(self):
        return
        
    # minimax implementation

    # state: the current board state
    # alpha: MAX score along the path to state
    # beta: MIN score along the path to state
    
    # depth: the depth of the search
    
    def max_value(self, state: Board, alpha, beta, colour, depth):
        board = state.board
        
        new_colour = ENEMY[colour]
        #print()
        #print("depth = ",depth)
        #print(render_board(state.board))

        if countColour(board,'r') == 0:
            #print("evaluation = ",-1000)
            return -1000
        elif countColour(board,'b') == 0:
            #print("evaluation = ",1000)
            return 1000

        if peaceful(board): # or state.turn > MAX_TURNS:
            #print("evaluation = ",evaluatePower(board))
            return evaluatePower(board)

        #if depth == 0:
        #    return evaluateAtkDef(board, new_colour)
        if depth == 0:
            #print("colour to move = ",colour)
            #print("evaluation = ",evaluateAtkDef(board,colour))
            return evaluateAtkDef(board, colour)[0]
        
        v = -math.inf
           
        #for s in get_successors(state, new_colour):
        #    v = max(v, self.min_value(s[0], alpha, beta, new_colour, depth - 1))

        #    alpha = max(alpha, v)
        #    if alpha >= beta:
        #        return beta
        for s in get_successors(state, colour):
            v = max(v, self.min_value(s[0], alpha, beta, new_colour, depth - 1))

            alpha = max(alpha, v)
            if alpha >= beta:
                return beta
            
        return v
    
    def min_value(self, state: Board, alpha, beta, colour, depth):
        board = state.board

        new_colour = ENEMY[colour]
        
        #print()
        #print("depth = ",depth)
        #print(render_board(state.board))

        if countColour(board, 'r') == 0:
            #print("evaluation = -1000")
            return -1000
        elif countColour(board, 'b') == 0:
            #print("evaluation = 1000")
            return 1000

        if peaceful(board): # or state.turn > MAX_TURNS:
            #print("evaluation = ",evaluatePower(board))
            return evaluatePower(board)

        #if depth == 0:
        #    return evaluateAtkDef(board, new_colour) 
        if depth == 0:
            #print("colour to move = ",colour)
            #print("evaluation = ",evaluateAtkDef(board,colour))
            return evaluateAtkDef(board, colour)[0] 
        
        v = math.inf
                
        #for s in get_successors(state, new_colour):
        #    v = min(v, self.max_value(s[0], alpha, beta, new_colour, depth - 1))

        #    if v <= alpha:
        #        return v
        #    beta = min(beta, v)
        for s in get_successors(state, colour):
            v = min(v, self.max_value(s[0], alpha, beta, new_colour, depth - 1))

            if v <= alpha:
                return v
            beta = min(beta, v)

        return v
    
    # colour should affect this algorithm
    def next_move(self, board: Board, colour):
        best_score = None
        alpha = -math.inf
        beta = math.inf
        next_move = None

        #if colour == 'r':
        #    best_score = -math.inf
        #    for s in get_successors(board, colour):
        #        score = self.min_value(s[0], alpha, beta, colour, DEPTH)

        #        if score > best_score:
        #            best_score = score
        #            next_move = s
        #        alpha = max(alpha, best_score)
        
        #else:
        #    best_score = math.inf
        #    for s in get_successors(board, colour):
        #        score = self.max_value(s[0], alpha, beta, colour, DEPTH)

        #        if score < best_score:
        #            best_score = score
        #            next_move = s
        #        beta = min(beta, best_score)
        if colour == 'r':
            best_score = -math.inf
            for s in get_successors(board, colour):
                #print("current successor for red")
                #print(render_board(s[0].board))
                score = self.min_value(s[0], alpha, beta, ENEMY[colour], DEPTH - 1)
                
                if score > best_score:
                    best_score = score
                    next_move = s
                    #print("new best score found for red")
                    #print(score)
                    #print(render_board(s[0].board))
                alpha = max(alpha, best_score)
        
        else:
            best_score = math.inf
            for s in get_successors(board, colour):
                score = self.max_value(s[0], alpha, beta, ENEMY[colour], DEPTH - 1)

                if score < best_score:
                    best_score = score
                    next_move = s
                beta = min(beta, best_score)
        
        return next_move[1]

################################################################################
############################### End Program ####################################
################################################################################
def apply_ansi(str, bold=True, color=None):
    """
    Wraps a string with ANSI control codes to enable basic terminal-based
    formatting on that string. Note: Not all terminals will be compatible!

    Arguments:

    str -- String to apply ANSI control codes to
    bold -- True if you want the text to be rendered bold
    color -- Colour of the text. Currently only red/"r" and blue/"b" are
        supported, but this can easily be extended if desired...

    """
    bold_code = "\033[1m" if bold else ""
    color_code = ""
    if color == "r":
        color_code = "\033[31m"
    if color == "b":
        color_code = "\033[34m"
    return f"{bold_code}{color_code}{str}\033[0m"

def render_board(board: 'dict[tuple, tuple]', ansi=False) -> str:
    """
    Visualise the Infexion hex board via a multiline ASCII string.
    The layout corresponds to the axial coordinate system as described in the
    game specification document.
    
    Example:

        >>> board = {
        ...     (5, 6): ("r", 2),
        ...     (1, 0): ("b", 2),
        ...     (1, 1): ("b", 1),
        ...     (3, 2): ("b", 1),
        ...     (1, 3): ("b", 3),
        ... }
        >>> print_board(board, ansi=False)

                                ..     
                            ..      ..     
                        ..      ..      ..     
                    ..      ..      ..      ..     
                ..      ..      ..      ..      ..     
            b2      ..      b1      ..      ..      ..     
        ..      b1      ..      ..      ..      ..      ..     
            ..      ..      ..      ..      ..      r2     
                ..      b3      ..      ..      ..     
                    ..      ..      ..      ..     
                        ..      ..      ..     
                            ..      ..     
                                ..     
    """
    dim = 7
    output = ""
    for row in range(dim * 2 - 1):
        output += "    " * abs((dim - 1) - row)
        for col in range(dim - abs(row - (dim - 1))):
            # Map row, col to r, q
            r = max((dim - 1) - row, 0) + col
            q = max(row - (dim - 1), 0) + col
            if (r, q) in board:
                color, power = board[(r, q)]
                text = f"{color}{power}".center(4)
                if ansi:
                    output += apply_ansi(text, color=color, bold=False)
                else:
                    output += text
            else:
                output += " .. "
            output += "    "
        output += "\n"
    return output