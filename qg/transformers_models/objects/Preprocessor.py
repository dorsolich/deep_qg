
from qg.config.config import get_logger
_logger = get_logger(logger_name=__file__)

class DataProcessorObject:
    def __init__(self, sep_token, eos_token, setting = "") -> None:
        self.sep_token = sep_token
        self.eos_token = eos_token
        self.setting = setting

        self.prev_context = ""
        self.prev_questions = ""
        self.index = 0
        self.relevant_examples_indices = []
        self.init_indices = []
        self.len_answers = 0

    def process(self, dataset):

        # Experiment 1: one question per line
        if self.setting == "OQPL": 
            dataset = dataset.map(self._one_question_per_line)
        
        # Experiment 2: all questions per line
        elif self.setting == "AQPL": # all questions per line
            self.check_dataset = dataset
            dataset = dataset.map(self._all_questions_per_line)

        # Experiment 3: answer awareness
        elif self.setting == "AA":
            dataset = dataset.map(self._answers_awareness)

        # Experiment 4: basic processing
        dataset = dataset.map(self._eos_token)

        return dataset

    def _eos_token(self, example):
        example["context"] = example["context"] + self.eos_token
        example["question"] = example["question"] + self.eos_token
        return example

    def _one_question_per_line(self, example):
        example["context"] = example["context"] + self.eos_token + example["question"]
        return example

    def _all_questions_per_line(self, example):

        if example["context"] == self.prev_context:
            self.prev_questions += example["question"] + self.sep_token
            example["question"] = self.prev_questions
            self.prev_context = example["context"]

            self.index = 1 + self.index # modify this line if you are running cache errors running AQPL setting
            # self.index += 1 # modify this line if you are running cache errors running AQPL setting

        else:
            self.prev_questions = example["question"] + self.sep_token
            self.prev_context = example["context"]
            if self.index != 0:
                self.relevant_examples_indices.append(self.index-1)
            
            # self.index += 1
            self.index = 1 + self.index

        return example

    def _answers_awareness(self, ex):
        init_answer_token = "[ANSS] "
        end_answer_token = " [ANSE]"
        
        # Examples that don't contain answers
        if ex["answers"]["answer_start"] == []:
            return ex
        else:
            # Examples might contain more that one answer
            for i in range(len(ex["answers"]["answer_start"])):
                
                if i == 0:
                    i_init = ex["answers"]["answer_start"][i]
                else:
                    i_init = ex["answers"]["answer_start"][i] + (len(init_answer_token)*i)

                str_context = str(ex["context"])
                ex["context"] = str_context[:i_init] + init_answer_token + str_context[i_init:]
                self.init_indices.append(i_init)

            for i in range(len(ex["answers"]["answer_start"])):

                if i == 0:
                    i_end = self.init_indices[i] + len(init_answer_token) + len(ex["answers"]["text"][0])
                    self.len_answers += len(ex["answers"]["text"][0])
                else:
                    i_end = self.init_indices[i] + len(init_answer_token)*i+1 + self.len_answers

                str_context = str(ex["context"])
                ex["context"] = str_context[:i_end] + end_answer_token + str_context[i_end:]

            return ex

    def filter_examples(self, processed_train_data):

        # only applicable in setting AQPL
        if self.setting == "AQPL":
            _logger.info("WARNING: PREPROCESSING FOR AQPL")

            # due to cache memory issues, self.relevant_examples_indices might be an empty list
            # this if statement checks it and populates the variable "relevant_examples_indices" if needed
            if self.relevant_examples_indices == []:
                self.check_dataset = self.check_dataset.map(self._all_questions_per_line)
            
            processed_train_data = processed_train_data.select(self.relevant_examples_indices)
            
            _logger.info(f"""Filtered in {len(self.relevant_examples_indices)}, 
            filtered out {len(processed_train_data) - len(self.relevant_examples_indices)}""")
            
        return processed_train_data
