from qg.config.config import get_logger, device
_logger = get_logger(logger_name=__name__)
_logger.info(f"""Running in device: {device}""")



class Decoder:
    def __init__(self, device) -> None:
        self.device = device
        self.contexts = []
        self.questions = []
        self.generated_questions = []
        self.prev_passage = ""

    def decode_example(self, example):
        decode = True
        self.context = example["context"].replace('\n', '')
        self.question = example["question"]
        
        # scaping passages that eather look the same as the previous or
        # hasn't got answers
        if (len(example["answers"]["text"])==0 or 
            self.context==self.prev_passage): 
            decode = False

        # update prev passage variable
        self.prev_passage = self.context
        return decode
        
    def tokenize(self,
                tokenizer, 
                max_length_source = 512, 
                truncation = True, 
                padding = "max_length",
                return_tensors = "pt"
                ):
        
        self.tokenizer = tokenizer
        encodings = self.tokenizer(self.context, truncation=truncation, max_length=max_length_source, padding=padding, return_tensors=return_tensors)
        self.source_ids = encodings['input_ids'].to(self.device)
        self.source_attention_mask = encodings['attention_mask'].to(self.device)

        return self

    def decode(self, 
                model, 
                num_beams,  
                question_max_length = 32, 
                repetition_penalty = 2.5,
                length_penalty = 1,
                early_stopping = True,
                use_cache = True,
                num_return_sequences = 1,
                do_sample = False,
                ):

        generated_target_ids = model.generate(
            input_ids = self.source_ids,
            attention_mask = self.source_attention_mask,
            num_beams = num_beams, 
            do_sample = do_sample,
            max_length = question_max_length,
            repetition_penalty = repetition_penalty,
            length_penalty = length_penalty,
            early_stopping = early_stopping,
            use_cache = use_cache,
            num_return_sequences = num_return_sequences
        )
        for generated_target_id in generated_target_ids:
            generated_questions = self.tokenizer.decode(generated_target_id,
                                                        skip_special_tokens=True,
                                                        clean_up_tokenization_spaces=True
                                                        )

            self.generated_questions.append(generated_questions)
            self.contexts.append(self.context)
            self.questions.append(self.question)

        return self