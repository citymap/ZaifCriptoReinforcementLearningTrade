import sys
import gym
import pylab
import random
import numpy as np
from collections import deque
from keras.layers import Dense
from keras.optimizers import Adam
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import Input
from keras.layers import Add,Conv1D,Flatten,Concatenate
from keras.models import Model
from functions import *
#from keras.utils import plot_model
EPISODES = 300

# Double DQN Agent for the Cartpole
# it uses Neural Network to approximate q function
# and replay memory & target q network
class DoubleDQNAgent:
    def __init__(self, state_size, action_size,max_inventory):
        # if you want to see Cartpole learning, then change to True
        self.render = False
        self.load_model = False #True
        # get size of state and action
        self.state_size = state_size
        self.action_size = action_size
        self.input_stream_size=7
        # these is hyper parameters for the Double DQN
        self.discount_factor = 0.97
        self.learning_rate = 0.0005
        self.epsilon = 0.3
        self.epsilon_decay = 0.99999
        self.epsilon_min = 0.05
        self.batch_size = 128
        self.train_start = 1000
        self.buy_sell_len=2
        self.max_inventory=max_inventory
        # create replay memory using deque
        self.memory = deque(maxlen=2000)

        # create main model and target model
        self.model = self.build_model()
        self.target_model = self.build_model()

        # initialize target model
        self.update_target_model()

        if self.load_model:
            self.model.load_weights("./save_model/epoch8_300000ddqn.h5")

    # approximate Q function using Neural Network
    # state is input and Q Value of each action is output of network
    def build_model(self):
        input1 = Input(batch_shape=(None,1, self.state_size), name="in1")
        x1 = Conv1D(10,10,strides=1,padding="causal",dilation_rate=4)(input1)
        input2 = Input(batch_shape=(None,1, self.state_size), name="in2")
        x2 = Conv1D(10,10,strides=1,padding="causal",dilation_rate=4)(input2)
        input3 = Input(batch_shape=(None,1, self.state_size), name="in3")
        x3 = Conv1D(10,10,strides=1,padding="causal",dilation_rate=4)(input3)
        input4 = Input(batch_shape=(None,1, self.state_size), name="in4")
        x4 = Conv1D(10,10,strides=1,padding="causal",dilation_rate=4)(input4)
        input5 = Input(batch_shape=(None,1, self.state_size), name="in5")
        x5 = Conv1D(10,10,strides=1,padding="causal",dilation_rate=4)(input5)
        input6 = Input(batch_shape=(None,1, self.state_size), name="in6")
        x6 = Conv1D(10,10,strides=1,padding="causal",dilation_rate=4)(input6)
        input7 = Input(batch_shape=(None,1, self.state_size), name="in7")
        x7 = Conv1D(10,10,strides=1,padding="causal",dilation_rate=4)(input7)
        buy_sell = Input(batch_shape=(None,1, self.buy_sell_len), name="buy_sell")
        x8 = Dense(30,activation='relu')(buy_sell)
        buy_inventory = Input(batch_shape=(None,1, self.max_inventory), name="buy_inventory")
        x9 = Dense(30,activation='relu')(buy_inventory)
        sell_inventory = Input(batch_shape=(None,1,self.max_inventory), name="sell_inventory")
        x10 = Dense(30,activation='relu')(sell_inventory)

        added = Add()(
            [x1, x2, x3, x4, x5, x6, x7])  # equivalent to added = keras.layers.add([x1, x2])
        added_dense = Add()([x8,x9,x10])
        fl1=Flatten()(added)
        fl2=Flatten()(added_dense)
        fl_add=Concatenate(axis=1)([fl1,fl2])
        dense_added = Dense(400)(fl_add)
        out = Dense(self.action_size, activation="sigmoid", name="output_Q")(dense_added)
        model = Model(inputs=[input1, input2, input3, input4, input5, input6, input7, buy_sell,buy_inventory,sell_inventory],
                                   outputs=[out])

        model.compile(loss={'output_Q': 'mean_squared_error'},
                      loss_weights={'output_Q': 1},
                      optimizer=Adam(lr=0.001))

        #plot_model(model, to_file='model.png')
        return model

    # after some time interval update the target model to be same with model
    def update_target_model(self):
        self.target_model.set_weights(self.model.get_weights())

    # get action from model using epsilon-greedy policy
    def get_action(self, state,buy_sell,buy_inventory,sell_inventory):
        if np.random.rand() <= self.epsilon:
            return random.randrange(self.action_size)
        else:
            q_value = self.model.predict(({"in1":np.array([[state[0]]]),
                                           "in2":np.array([[state[1]]]),
                                           "in3": np.array([[state[2]]]),
                                           "in4": np.array([[state[3]]]),
                                           "in5": np.array([[state[4]]]),
                                           "in6": np.array([[state[5]]]),
                                           "in7": np.array([[state[6]]]),
                                           "buy_sell": np.array([[buy_sell]]),
                                           "buy_inventory":np.array([[buy_inventory]]),
                                           "sell_inventory":np.array([[sell_inventory]])}))
            print(q_value)
            return np.argmax(q_value[0])

    # save sample <s,a,r,s'> to the replay memory
    def append_sample(self, state, action, reward, next_state, done,buy_sell,next_buy_sell,current_buy_inv,current_sell_inv):
        self.memory.append((state, action, reward, next_state, done,buy_sell,next_buy_sell,current_buy_inv,current_sell_inv))
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

    # pick samples randomly from replay memory (with batch_size)
    def train_model(self):
        if len(self.memory) < self.train_start:
            return
        batch_size = min(self.batch_size, len(self.memory))
        mini_batch = random.sample(self.memory, batch_size)

        update_input = np.zeros((batch_size,self.input_stream_size,self.state_size))
        update_target = np.zeros((batch_size,self.input_stream_size,self.state_size))
        update_input_buy_sell=np.zeros((batch_size,1,self.buy_sell_len))
        update_target_buy_sell=np.zeros((batch_size,1,self.buy_sell_len))
        update_input_buy_inventory=np.zeros((batch_size,1,self.max_inventory))
        update_input_sell_inventory=np.zeros((batch_size,1,self.max_inventory))

        action, reward, done = [], [], []

        for i in range(batch_size):
            update_input[i] = mini_batch[i][0]
            action.append(mini_batch[i][1])
            reward.append(mini_batch[i][2])
            update_target[i] = mini_batch[i][3]
            done.append(mini_batch[i][4])
            update_input_buy_sell[i]=mini_batch[i][5]
            update_target_buy_sell[i]=mini_batch[i][6]
            update_input_buy_inventory[i]=mini_batch[i][7]
            update_input_sell_inventory[i]=mini_batch[i][8]

        update_input=update_input.reshape((batch_size,self.input_stream_size,1,self.state_size))
        update_target=update_target.reshape((batch_size,self.input_stream_size,1,self.state_size))
        update_input_buy_sell.reshape((batch_size,1,self.buy_sell_len))
        update_target_buy_sell.reshape((batch_size,1,self.buy_sell_len))
        update_input_buy_inventory.reshape((batch_size,1,self.max_inventory))
        update_input_sell_inventory.reshape((batch_size,1,self.max_inventory))

        #TODO buy_sell_arrayを修正する
        # (1,1,128,30)
        target = self.model.predict(({"in1":np.array(update_input[:,0]),
                                           "in2":np.array(update_input[:,1]),
                                           "in3": np.array(update_input[:,2]),
                                           "in4": np.array(update_input[:,3]),
                                           "in5": np.array(update_input[:,4]),
                                           "in6": np.array(update_input[:,5]),
                                           "in7": np.array(update_input[:,6]),
                                           "buy_sell": np.array(update_input_buy_sell),
                                           "buy_inventory": np.array(update_input_buy_inventory),
                                           "sell_inventory": np.array(update_input_sell_inventory),
                                           }))

        target_next = self.model.predict(({"in1":np.array(update_target[:,0]),
                                           "in2":np.array(update_target[:,1]),
                                           "in3": np.array(update_target[:,2]),
                                           "in4": np.array(update_target[:,3]),
                                           "in5": np.array(update_target[:,4]),
                                           "in6": np.array(update_target[:,5]),
                                           "in7": np.array(update_target[:,6]),
                                           "buy_sell": np.array(update_target_buy_sell),
                                           "buy_inventory": np.array(update_input_buy_inventory),
                                           "sell_inventory": np.array(update_input_sell_inventory)
                                           }))

        #self.model.predict(update_target)
        target_val = self.target_model.predict(({"in1":np.array(update_target[:,0]),
                                           "in2":np.array(update_target[:,1]),
                                           "in3": np.array(update_target[:,2]),
                                           "in4": np.array(update_target[:,3]),
                                           "in5": np.array(update_target[:,4]),
                                           "in6": np.array(update_target[:,5]),
                                           "in7": np.array(update_target[:,6]),
                                           "buy_sell": np.array(update_target_buy_sell),
                                           "buy_inventory": np.array(update_input_buy_inventory),
                                           "sell_inventory": np.array(update_input_sell_inventory)
                                           }))

        for i in range(self.batch_size):
            # like Q Learning, get maximum Q value at s'
            # But from target model
            if done[i]:
                target[i][action[i]] = reward[i]
            else:
                # the key point of Double DQN
                # selection of action is from model
                # update is from target model
                a = np.argmax(target_next[i])
                #print(i)#64
                #print("a:" + str(a))#a:0
                target[i][action[i]] = reward[i] + self.discount_factor * (
                    target_val[i][a])

        # make minibatch which includes target q value and predicted q value
        # and do the model fit!
        # update_input
        self.model.fit({"in1": np.array(update_target[:, 0]),
                                           "in2": np.array(update_target[:, 1]),
                                           "in3": np.array(update_target[:, 2]),
                                           "in4": np.array(update_target[:, 3]),
                                           "in5": np.array(update_target[:, 4]),
                                           "in6": np.array(update_target[:, 5]),
                                           "in7": np.array(update_target[:, 6]),
                                           "buy_sell": np.array(update_target_buy_sell),
                                           "buy_inventory": np.array(update_input_buy_inventory),
                                           "sell_inventory": np.array(update_input_sell_inventory)
                                                                                  }, target, batch_size=self.batch_size,
                       epochs=1, verbose=0)


if __name__ == "__main__":

    window_size, episode_count = int(30), int(1000)

    print("window_size:" + str(window_size))
    print("episode_count:" + str(episode_count))

    data = read_bitflyer_json()

    length_data = len(data) - 1
    action_size = 5
    max_inventory=50
    agent = DoubleDQNAgent(window_size, action_size,max_inventory)
    scores, episodes = [], []

    for e in range(EPISODES):
        done = False
        total_profit = 0
        agent.buy_inventory = []
        agent.sell_inventory = []
        for idx in range(length_data):
            state = getStateFromCsvData(data, idx, window_size)

            # get action for the current state and go one step in environment
            # action =
            # next_state, reward, done, info = env.step(action)
            len_buy = len(agent.buy_inventory)
            len_sell = len(agent.sell_inventory)
            buy_sell = [len_buy, len_sell]

            current_buy_inv,current_sell_inv = make_inventory_array(agent.buy_inventory,
                                                agent.sell_inventory,max_inventory=max_inventory,current_price=data[idx])
            #state.append(buy_sell_array)
            #TODO buy_sell_array_nextを設定する。
            action = agent.get_action(state,buy_sell,current_buy_inv,current_sell_inv)
            # TODO idx + 1出なくて良いか？　バグの可能性あり。
            next_state = getStateFromCsvData(data, idx + 1, window_size)

            reward = 0

            if action == 1 and len(agent.buy_inventory) < max_inventory:
                agent.buy_inventory.append(data[idx])
                next_buy_sell=[len_buy+1,len_sell]
                print("Buy: " + formatPrice(data[idx]))
            elif action == 2 and len(agent.sell_inventory) > 0:
                sold_price = agent.sell_inventory.pop(0)
                profit = sold_price - data[idx]
                reward += profit  # max(profit, 0)
                total_profit += profit
                next_buy_sell = [len_buy,len_sell-1]
                print("Buy(決済): " + formatPrice(data[idx]) + " | Profit: " + formatPrice(profit))
            elif action == 3 and len(agent.sell_inventory) < max_inventory:
                agent.sell_inventory.append(data[idx])
                next_buy_sell=[len_buy,len_sell+1]
                print("Sell(空売り): " + formatPrice(data[idx]))
            elif action == 4 and len(agent.buy_inventory) > 0:
                bought_price = agent.buy_inventory.pop(0)
                profit = data[idx] - bought_price
                reward += profit  # max(profit, 0)
                total_profit += profit
                next_buy_sell = [len_buy-1,len_sell]
                print("Sell: " + formatPrice(data[idx]) + " | Profit: " + formatPrice(profit))
            else:
                next_buy_sell=[len_buy,len_sell]

            if reward > 0:
                sigmoid(reward * 0.001)
            else:
                sigmoid(reward * 0.0005)
            print("act:"+str(action)+"|| buy_sell:"+str(buy_sell)+" || next_buy_sell"+str(next_buy_sell))
            #next_buy_inv,next_sell_inv = make_inventory_array(agent.buy_inventory,agent.sell_inventory,max_inventory=max_inventory)
            # save the sample <s, a, r, s'> to the replay memory
            agent.append_sample(state, action, reward, next_state, done,buy_sell,next_buy_sell,current_buy_inv,current_sell_inv)
            # every time step do the training
            agent.train_model()
            update_trading_view(data[idx],action)
            state = next_state

            if idx % 10 == 0:
                print("--------------------------------")
                print("Total Profit: " + formatPrice(total_profit))
                print("BUY SELL" + str(buy_sell))
                print("--------------------------------")
            if idx == 10000:
                #draw_trading_view()
                pass
            if idx % 100000 == 0:
                agent.model.save_weights("./save_model/epoch"+str(e)+"_"+str(idx)+"ddqn.h5")
