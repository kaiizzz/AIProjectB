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

# This is the entry point for your game playing agent. the agent will do an
# action given the state of the board through the calculations of minimax 
# algorithm with alpha-beta pruning.

# intitialise the constants
BREADTH = 6
DEPTH = 4

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
        self.Minimax = minimax()
        
        # select the match color:
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
        # if its not at an end game situation find best move VIA minimax
        next_move = self.Minimax.next_move(self.board, self.colour)

        # return the action    
        if (next_move[0] == 'spread'):
                return SpreadAction(HexPos(next_move[1][0], next_move[1][1]), HexDir(next_move[2]))
        else:
                return SpawnAction(HexPos(next_move[1][0], next_move[1][1]))
       
    
    def turn(self, color: PlayerColor, action: Action, **referee: dict):
        """
        Update the agent with the last player's action.
        Note: this updates your agent as well.
        """

        match action:
            case SpawnAction(cell):
                c = 'r'
                if (color == PlayerColor.BLUE):
                    c = 'b'
                self.board.spawn((cell.r, cell.q), c)
                return
            case SpreadAction(cell, direction):
                self.board.spread((cell.r, cell.q), (direction.value.r, direction.value.q))
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


################################################################################
######################## Minimax helper functions ##############################
################################################################################   
    
def get_root_successors(state: Board, colourToMove):
    """ gets the successors, possible states we need to explore """
    successors = []

    # do we need to copy board into state? just use the board argument
    temp = copy.deepcopy(state)
    
   
    # initialise the coverages
    coverages = getCoverages(state.board)
    colourToMoveCoverage = None
    colourJustPlayedCoverage = None

    # set the coverages
    if colourToMove == 'r':
        colourToMoveCoverage = coverages[0]
        colourJustPlayedCoverage = coverages[1]
    else:
        colourToMoveCoverage = coverages[1]
        colourJustPlayedCoverage = coverages[0]
    
    # loop through the board and find all player's piece
    # when you land on a piece perform a spread in 6 directions
    # if it is empty spawn a piece
    # add to the successors list
    for position in state.board.keys():
        if(state.board.get(position)[0] == colourToMove):
            for direction in DIRECTIONS:
                temp.spread(position, direction)
                successors.append((temp, ('spread', position, direction)))
                temp = copy.deepcopy(state) # reset temp to original state
    
    # for spawn action
    if getTotalPower(state.board) < MAX_BOARD_POW:
        for r in range(DIM):
            for q in range(DIM):
                if (r,q) not in state.board.keys():
                    playerCoverage = colourToMoveCoverage[r,q]
                    if playerCoverage >= colourJustPlayedCoverage[(r,q)]:
                        temp.spawn((r, q), colourToMove)
                        # add the spawn to the successors
                        successors.append((temp, ('spawn', (r, q), colourToMove)))
                        temp = copy.deepcopy(state)

    bestForPower = None

    # person just moved is r --> next to move is b, vice versa
    if colourToMove == 'r':
        successors = sorted(successors, key = lambda x: evaluateAtkDef(x[0].board, 'b'), reverse=True)
        bestForPower = max(successors, key = lambda x: evaluatePower(x[0].board))
    else:
        successors = sorted(successors, key = lambda x: evaluateAtkDef(x[0].board, 'r'))
        bestForPower = min(successors, key = lambda x: evaluatePower(x[0].board))
    
    # choose the top 'b' successors
    b = min(len(successors), BREADTH)
    chosenSuccessors = successors[0:(b-1)]

    # add the board with best power as a greedy component to the list of successors to explore
    if bestForPower in chosenSuccessors:
        chosenSuccessors.remove(bestForPower)
    else:
        chosenSuccessors.pop()

    chosenSuccessors.insert(0, bestForPower)
    
    # return chosen list of successors
    return chosenSuccessors

def get_successors(state: Board, colourToMove):
    """ gets the successors, possible states we need to explore """
    successors = []

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
    
    for position in state.board.keys():
        if(state.board.get(position)[0] == colourToMove):
            for direction in DIRECTIONS:
                temp.spread(position, direction)
                successors.append(temp)
                temp = copy.deepcopy(state) # reset temp to original state
    
    if getTotalPower(state.board) < MAX_BOARD_POW:
        for r in range(DIM):
            for q in range(DIM):
                if (r,q) not in state.board.keys():
                    playerCoverage = colourToMoveCoverage[r,q]
                    if playerCoverage >= colourJustPlayedCoverage[(r,q)]:
                        temp.spawn((r, q), colourToMove)
                        successors.append(temp)
                        temp = copy.deepcopy(state)

    bestForPower = None
    # person just moved is r --> next to move is b, vice versa
    if colourToMove == 'r':
        successors = sorted(successors, key = lambda x: evaluateAtkDef(x.board, 'b'), reverse=True)
        bestForPower = max(successors, key = lambda x: evaluatePower(x.board))
    else:
        successors = sorted(successors, key = lambda x: evaluateAtkDef(x.board, 'r'))
        bestForPower = min(successors, key = lambda x: evaluatePower(x.board))
    
    # choose the top 'b' successors
    b = min(len(successors), BREADTH)
    chosenSuccessors = successors[0:(b-1)]

    # add the board with best power as a greedy component to the list of successors to explore
    if bestForPower in chosenSuccessors:
        chosenSuccessors.remove(bestForPower)
    else:
        chosenSuccessors.pop()

    chosenSuccessors.insert(0, bestForPower)
      
    return chosenSuccessors



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
    """
    Returns the sum of powers on the board
    """

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
       
        if countColour(board,'r') == 0:
            return -1000
        elif countColour(board,'b') == 0:
            return 1000

        if peaceful(board):
            return evaluatePower(board)

        if depth == 0:
            return evaluateAtkDef(board, colour)[0]
        
        v = -math.inf
           
        for s in get_successors(state, colour):
            v = max(v, self.min_value(s, alpha, beta, new_colour, depth - 1))

            alpha = max(alpha, v)
            if alpha >= beta:
                return beta
            
        return v
    
    def min_value(self, state: Board, alpha, beta, colour, depth):
        board = state.board
        new_colour = ENEMY[colour]
        
        if countColour(board, 'r') == 0:
            return -1000
        elif countColour(board, 'b') == 0:
            return 1000

        if peaceful(board): 
            return evaluatePower(board)

        if depth == 0:
            return evaluateAtkDef(board, colour)[0] 
        
        v = math.inf
                
        for s in get_successors(state, colour):
            v = min(v, self.max_value(s, alpha, beta, new_colour, depth - 1))

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

        if colour == 'r':
            best_score = -math.inf
            for s in get_root_successors(board, colour):
                
                score = self.min_value(s[0], alpha, beta, ENEMY[colour], DEPTH - 1)
                
                if score > best_score:
                    best_score = score
                    next_move = s
                alpha = max(alpha, best_score)
        
        else:
            best_score = math.inf
            for s in get_root_successors(board, colour):
                score = self.max_value(s[0], alpha, beta, ENEMY[colour], DEPTH - 1)

                if score < best_score:
                    best_score = score
                    next_move = s
                beta = min(beta, best_score)
        
        return next_move[1]

################################################################################
############################### End Program ####################################
################################################################################
